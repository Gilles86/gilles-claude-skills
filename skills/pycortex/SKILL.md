---
name: pycortex
description: Gotchas and best practices for pycortex (cortical-surface visualization / webgl viewer) — why `cortex.webgl.show()` often "doesn't load" (the server's daemon thread dies the instant your script exits; the auto-opened URL uses the machine hostname instead of localhost), the pycortex2-vs-heavy-env split, `VertexRGB`/`blend_curvature` vs `Vertex2D` for alpha/threshold display (baked-in vs live), and why R²-shaped auto-threshold code silently breaks on cvR²-like data that can be negative. Use whenever calling `cortex.webgl.show`, `cortex.Vertex`/`VertexRGB`/`Vertex2D`, `blend_curvature`, or debugging a pycortex viewer that won't load, shows a blank page, or crashes with a cryptic `TypeError`.
---

# pycortex — gotchas and best practices

Distilled from repeated pycortex sessions on abstract_values (group cvR²/R²
flatmaps and interactive webshows). Pycortex is powerful but rough around
the edges — most failures are silent, or produce errors far from the real
root cause. This skill exists to shortcut that debugging loop.

## Golden rules

**1. A `cortex.webgl.show()` server dies the instant your script returns —
it does not run as an independent process.**

`WebApp` (`cortex/webgl/serve.py`) is a `daemon=True` `threading.Thread`.
When you call `cortex.webgl.show(ds)` from a plain script (`python -m
foo.py`, or any launcher with no code after the call) and the interpreter
exits, the daemon thread is killed with it — often within seconds, and
sometimes before the browser has even finished pulling all the CTM/surface
assets, which makes the page look permanently "stuck loading" even though
the server *did* briefly work. This is why running interactively (IPython,
a Jupyter cell, `python -i`) "just works": the REPL process never exits on
its own, so the thread survives for as long as you keep the session open.

For a script or background-task launch, you must keep the main thread
alive yourself after starting the server. See
[`references/persistent_webshow.py`](./references/persistent_webshow.py)
for the full pattern; the essential shape:

```python
server = cortex.webgl.show(ds, open_browser=False, autoclose=False)
url = f"http://localhost:{server.port}/mixer.html"
subprocess.run(["open", url])   # macOS; opens the *correct* URL yourself
while True:
    time.sleep(3600)            # keep the daemon thread alive
```

**2. The auto-opened browser URL uses your hostname, not `localhost` — and
that usually fails to load.**

`cortex.webgl.show(..., open_browser=True)` (the default) builds the URL
as `http://<hostname><domain>:<port>/mixer.html` (from `serve.hostname`),
not `http://localhost:<port>`. On most laptops that hostname doesn't
resolve/connect from the browser, so the auto-opened tab shows a
"can't reach this page" error even when the server itself is fine. Fix:
manually replace the hostname with `localhost` in the address bar — or
better, don't rely on the auto-open at all: pass `open_browser=False`,
build the URL yourself with `localhost`, and open it explicitly
(`subprocess.run(["open", url])` on macOS). Combine with rule 1's
keep-alive pattern; both bugs independently make the viewer look "broken"
even though the underlying computation was fine.

**3. Two conda environments — don't mix them.**

`pycortex2` (pycortex + numpy/nibabel/scipy only, kept deliberately
minimal) for anything that touches `cortex.*` — viewing, `blend_curvature`,
`cortex.webgl.show`. The project's heavy analysis env (nilearn/nipype/TF)
for anything that *produces* the surface data in the first place
(`nilearn.surface.vol_to_surf`, FreeSurfer `SurfaceTransform` via nipype).
Installing nilearn/TF into `pycortex2` just to avoid the split invites
dependency conflicts with pycortex's own numpy/scipy pins; keep
surface-sampling scripts import-light instead so more of them can run in
`pycortex2` too.

## `VertexRGB` / `blend_curvature()` vs `Vertex2D` — the alpha-channel trap

Pycortex's live webgl viewer has real alpha/threshold sliders for
`Volume` data, but **not for `Vertex` data** — a long-standing, still-open
limitation
([gallantlab/pycortex#323](https://github.com/gallantlab/pycortex/issues/323)).
Three ways to get color+threshold onto a vertex map, in order of how
"alive" the result stays after `show()`:

| Approach | What it is | Threshold is | Caveat |
|---|---|---|---|
| `cortex.Vertex(...).blend_curvature(alpha)` | Pre-blends data + curvature into one RGB image, in Python, before showing | **Baked in at call time** | The docstring says it outright: *"the colormap parameters (vmin, vmax, cmap, ...) of the original Vertex object cannot be changed later on."* No live slider, ever. Started life as a community kludge (issue #323's thread) and was later formalized as this method in [PR #425](https://github.com/gallantlab/pycortex/pull/425) — useful, but still a workaround, not first-class transparency support. |
| `cortex.Vertex2D(dim1, dim2, ...)` | A true two-dimensional *joint* colormap (dim1 × dim2, e.g. effect × R²), rendered live in webgl | Live-adjustable (`vmin`/`vmax`/`vmin2`/`vmax2`) | Needs a proper 2D colormap image configured (`default_cmap2d` in `options.cfg`); dim2 is a joint-colormap axis (hue×saturation-style), not literally an opacity fade — reads differently from a transparency-based threshold. |
| `cortex.VertexRGB(r, g, b, subject)` | Manually packed RGB(A) arrays | Whatever you baked in | Lowest level; `blend_curvature()` is built directly on this. |

**Practical implication:** if you use `blend_curvature()` (as this
project's `visualize_mean_r2_fsaverage.py` does), pick your threshold
*before* calling `show()` — there is no way to tune it afterward in the
browser. Iterate on threshold values in Python and relaunch, rather than
expecting a slider.

**A NaN threshold silently corrupts `blend_curvature`, and the resulting
crash is nowhere near the actual cause.** Its alpha handling is
`alpha = np.clip(alpha, 0, 1)` — no NaN guard. `np.clip` does not turn NaN
into 0 or 1; it stays NaN. `nan * data + (1 - nan) * curvature` is
all-NaN, and `.astype("uint8")` on NaN is undefined behavior — numpy
emits `RuntimeWarning: invalid value encountered in cast` and, on this
platform, yields 0 — so **every affected dataset collapses to an
identical, all-black RGB image**. Pycortex names/dedups datasets inside
`Package` by a content hash of that RGB array
(`VertexRGB.name = "__" + hash(vertices)[:16]`), so multiple NaN-thresholded
datasets silently collide onto the same hash key. `Package.reorder()`
isn't dedup-aware, so it reprocesses that same slot twice — the second
pass finds the already-serialized `bytes` from the first pass instead of
the original ndarray, and dies with:

```
TypeError: byte indices must be integers or slices, not tuple
```

This error has nothing to do with byte indexing conceptually. **It means
two or more of the datasets you're showing rendered to bit-identical
images**, almost always because a threshold/vmin/vmax computation silently
produced NaN somewhere upstream. Before chasing the traceback, print
`vmin`/`vmax`/your threshold variable for every dataset about to be
shown and look for NaN.

## Don't feed cvR²-shaped data through R²-shaped auto-threshold code

Full-fit encoding-model R² (non-negative, bounded `[0, 1]`) and
cross-validated R² / cvR² (which **can be legitimately negative** for
noise/weak voxels — a silent voxel's held-out fit is *expected* to score
slightly below the train-mean baseline) look similar but are not
interchangeable for auto-thresholding code. A logit-transform /
empirical-null threshold fitter that filters its input to the open
interval `(0, 1)` will silently discard the entire negative bulk of a
cvR² map. If most of the map is negative — completely normal for cvR² —
too few points survive the filter, the threshold fitter returns NaN, and
you land straight in the `blend_curvature` hash-collision bug above.

Two ways out:

- Use (or write) a threshold method with an explicit non-degenerate
  fallback — e.g. falling back to a raw percentile of the *untransformed*
  data when the logit-domain fit fails — rather than one that can return
  NaN outright with no fallback.
- Better, specifically for cvR²: don't threshold the group mean at all.
  Compare **per-subject, per-vertex**, `cvR² > cvR²_null` (a proper null
  model's cvR², not a flat `> 0`), then display **prevalence** — the
  fraction of subjects where the real model wins at that vertex — rather
  than the raw group-mean magnitude. Binarizing per subject before
  pooling also keeps very-negative noise vertices from dominating a naive
  cross-subject average.

## Group-vertex maps read as sparse/speckled — that's not (necessarily) a bug

A prevalence-style or raw group-mean map computed **per vertex** on
fsaverage can look extremely speckled even when there's real, robust
signal underneath, because:

- Individual anatomical differences plus imperfect fsaverage surface
  registration mean the *exact* vertex carrying peak signal drifts from
  subject to subject; a strict per-vertex vote rarely lines up across 20+
  people.
- Unsmoothed single-subject model fits are inherently noisy at the
  voxel/vertex level.

Spatial (BOLD, pre-fit) smoothing trades vertex-level precision for
group-level coherence — worth comparing smoothed vs. unsmoothed side by
side rather than picking one. If a baseline/reference model's smoothed
variant hasn't been fit for every subject, a smoothed *prevalence*
comparison against it will silently drop to whatever subset does have
smoothed data — check coverage before trusting a printed `n=`:

```bash
find <model-dir> -name "*_smoothed_pe.nii.gz" | wc -l
```

## Copy-pasteable

- [`references/persistent_webshow.py`](./references/persistent_webshow.py)
  — a launch pattern that survives both the daemon-thread-exit and
  hostname-URL gotchas above, safe to run under a background task runner.
  Swap in your own dataset-building code where marked.
