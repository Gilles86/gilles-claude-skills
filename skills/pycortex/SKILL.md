---
name: pycortex
description: Gotchas and best practices for pycortex (cortical-surface visualization / webgl viewer) — why `cortex.webgl.show()` often "doesn't load", the pycortex2-vs-heavy-env split, `VertexRGB`/`blend_curvature` vs `Vertex2D` for alpha/threshold display (baked-in vs live), why R²-shaped auto-threshold code silently breaks on cvR²-like data, `make_static` bundle traps, and driving a bundle from JavaScript (camera, `mix`, `setData`). References cover auto-flattening a cohort with autoflatten and writing real ROIs into `overlays.svg` from a vertex mask. Read it BEFORE any pycortex work — almost every failure here is silent or reported far from its cause. Use whenever calling `cortex.webgl.show`/`make_static`, `cortex.Vertex`/`VertexRGB`/`Vertex2D`, `blend_curvature`, `cortex.db.get_overlay`/`get_roi_verts`, `import_flat`/autoflatten, or writing ROIs into `overlays.svg`; and when debugging a pycortex viewer that won't load, shows a blank page or a stale overlay, hangs on an `overwrite overlays.svg?` prompt, or crashes with a cryptic `TypeError` or `BrokenProcessPool`.
---

# pycortex — gotchas and best practices

Pycortex is powerful and rough around the edges. Almost nothing here fails loudly:
a NaN threshold surfaces as a `TypeError` about byte indices, a missing FreeSurfer
license as a topology error, an unknown XLA flag as `BrokenProcessPool`, a stale
browser cache as "my rebuild did nothing". **Read this file before starting**, and
open the reference for the part you are about to touch — each carries the full recipe
and its traps:

| About to | Read first |
|---|---|
| flatten subjects that were never cut in Freeview | [`references/autoflatten.md`](./references/autoflatten.md) |
| write ROIs into `overlays.svg` from a vertex mask | [`references/roi_authoring.md`](./references/roi_authoring.md) |
| build a bundle with its own legend / landing page | [`references/static_bundle_with_legend.py`](./references/static_bundle_with_legend.py) |
| keep a live `webgl.show` alive from a script | [`references/persistent_webshow.py`](./references/persistent_webshow.py) |

Distilled from repeated sessions on abstract_values and tms_risk (group cvR²/R²
flatmaps, per-participant webgl bundles).

## Golden rules

**0. An AI assistant cannot see `cortex.webgl.show()` — render a static PNG and
actually look at it before reporting anything.** A script can run cleanly, print
plausible statistics, and still have produced a dataset that renders as a blank
curvature-only image — e.g. nothing survived a threshold, so `alpha` is 0 everywhere.
The printed numbers will not catch it. Render the same data with
`cortex.quickflat.make_figure(vtx, with_curvature=True)` → `savefig` and view the file.
This caught a genuinely broken figure whose log looked completely normal.

**1. A `cortex.webgl.show()` server dies the instant your script returns.** `WebApp`
(`cortex/webgl/serve.py`) is a `daemon=True` thread, so it is killed with the
interpreter — often before the browser finished pulling the CTM, which makes the page
look permanently "stuck loading". Interactive sessions (IPython, `python -i`) work only
because the REPL never exits. From a script, keep the main thread alive yourself:

```python
server = cortex.webgl.show(ds, open_browser=False, autoclose=False)
url = f"http://localhost:{server.port}/mixer.html"
subprocess.run(["open", url])   # macOS; opens the *correct* URL yourself
while True:
    time.sleep(3600)            # keep the daemon thread alive
```

**2. The auto-opened browser URL uses your hostname, not `localhost`.**
`show(..., open_browser=True)` builds `http://<hostname><domain>:<port>/mixer.html`,
which on most laptops does not resolve — the tab shows "can't reach this page" while the
server is fine. Pass `open_browser=False` and open a `localhost` URL yourself. Rules 1
and 2 independently make a working viewer look broken.

**3. Two conda environments — don't mix them.** `pycortex2` (pycortex + numpy/nibabel/
scipy, deliberately minimal) for anything touching `cortex.*`; the project's heavy env
(nilearn/nipype/TF) for anything that *produces* the surface data. Installing nilearn/TF
into `pycortex2` invites conflicts with pycortex's numpy/scipy pins; keep
surface-sampling scripts import-light instead.

**4. A freshly `freesurfer.import_subj()`-ed subject has NO flat map** — `quickflat`
(and any `blend_curvature` static PNG) hard-crashes with `KeyError: 'flat'` from
`db.get_surf(subject, "flat", ...)`. Flat maps need topological cuts, which `import_subj`
does not make. Either fall back to inflated renders (`nilearn.plotting.plot_surf_stat_map`
off `{hemi}.inflated` + `{hemi}.curv`) **and say that it is inflated, not flattened** — a
curvature-only quickflat substitute silently delivers something weaker than asked for — or
generate the cuts: [`references/autoflatten.md`](./references/autoflatten.md).

## `VertexRGB` / `blend_curvature()` vs `Vertex2D` — the alpha-channel trap

The webgl viewer has alpha/threshold sliders for `Volume` data but **not for `Vertex`
data** ([pycortex#323](https://github.com/gallantlab/pycortex/issues/323)). Three ways to
get colour + threshold onto a vertex map:

| Approach | What it is | Threshold is | Caveat |
|---|---|---|---|
| `cortex.Vertex(...).blend_curvature(alpha)` | Pre-blends data + curvature into one RGB image, in Python | **Baked in at call time** | Its own docstring: *"the colormap parameters ... cannot be changed later on."* No live slider, ever. Iterate on thresholds in Python and relaunch. |
| `cortex.Vertex2D(dim1, dim2, ...)` | A joint 2D colormap (e.g. effect × R²), rendered live | Live (`vmin`/`vmax`/`vmin2`/`vmax2`) | Needs a 2D `*_alpha` colormap; dim2 is a joint-colormap axis, not an opacity fade, and reads washed out next to Python-side compositing. |
| `cortex.VertexRGB(r, g, b, subject)` | Manually packed RGB arrays | Whatever you baked in | Lowest level; `blend_curvature` is built on it. |

For the standard look, build the curvature exactly as `blend_curvature` does —
`(curv > 0) * contrast + brightness` off `db.get_surfinfo(subject, smooth=20)` — and
blend it yourself. Soft/continuous curvature shading reads oddly next to pycortex's own.

**`quickflat.make_figure(..., with_colorbar=True)` on a baked image draws a colorbar,
but not YOUR colorbar** — there is no live `vmin`/`vmax`/`cmap` left to introspect, so it
falls back to a meaningless `0–255` swatch. Pass `with_colorbar=False` and annotate the
real range yourself.

**A NaN threshold silently corrupts `blend_curvature`, and the crash is nowhere near the
cause.** `np.clip` does not turn NaN into 0 or 1, so the blend is all-NaN and
`.astype("uint8")` yields 0 — every affected dataset collapses to an identical all-black
image. Pycortex keys datasets by a content hash of that array, `Package.reorder()` is not
dedup-aware, and the second pass finds serialized `bytes` where it expects an ndarray:

```
TypeError: byte indices must be integers or slices, not tuple
```

**It means two datasets rendered bit-identically**, almost always from a NaN threshold.
Print every dataset's `vmin`/`vmax`/threshold before chasing the traceback.

## Don't feed cvR²-shaped data through R²-shaped auto-threshold code

Full-fit R² is non-negative and bounded; cross-validated R² **can legitimately be
negative** (a silent voxel's held-out fit scores below the train-mean baseline). A
logit-transform / empirical-null threshold fitter that filters to the open interval
`(0, 1)` discards the entire negative bulk of a cvR² map, returns NaN, and lands you in
the hash-collision bug above. Either use a threshold method with a non-degenerate
fallback (a raw percentile of the untransformed data), or — better for cvR² — don't
threshold the group mean at all: test **per subject, per vertex**, `cvR² > cvR²_null`
against a real null model's cvR² (not a flat `> 0`) and display **prevalence**, the
fraction of subjects where the model wins. Binarising per subject before pooling also
stops very-negative noise vertices dominating the average.

## Group-vertex maps read as sparse/speckled — that's not (necessarily) a bug

Anatomical differences plus imperfect fsaverage registration mean the exact vertex
carrying peak signal drifts between subjects, and unsmoothed single-subject fits are
noisy — so a strict per-vertex vote rarely lines up across 20+ people. Spatial (BOLD,
pre-fit) smoothing buys group coherence at the cost of vertex precision; compare both
rather than picking one. If a reference model's smoothed variant was not fitted for
everyone, a smoothed prevalence map silently drops to whatever subset has it — check
coverage before trusting a printed `n=` (`find <model-dir> -name "*_smoothed_pe.nii.gz" | wc -l`).

## Prefer a static bundle over the live server

`cortex.webgl.make_static(outdir, ds, ...)` writes plain HTML/JS/binary that any file
server can host. Nothing depends on a live Python process, so rule 1 stops mattering, and
the output can be rsynced to a collaborator. Six traps:

- **`types` is for MORPH TARGETS only — never put `"flat"` in it.** Pycortex loads the
  flat surface itself and stores it as UV (that is what drives the flatten slider);
  `addSurf("flat")` renormalises it into the fiducial bounding box, and the flat z axis
  is constant, so the divide yields inf/NaN and OpenCTM rejects the mesh with a bare
  `CTM_INVALID_MESH`. Pass `types=("inflated",)`; flat comes along by itself.
- **`make_static` never deletes files it did not write this run.** Old payloads linger,
  unreferenced but accumulating (one bundle reached 235 MB against 85 MB clean). Clear
  `<outdir>/data/` first.
- **The generated page closes neither `</body>` nor `</html>`** — append, don't search
  for a closing tag to insert before.
- **`quickflat.make_figure` shells out to Inkscape** for ROI/sulci overlays; without it
  pass `with_rois=False, with_sulci=False, with_labels=False`.
- **`overlay_file=` is silently ignored whenever a `.ctm` is already cached.**
  `utils.get_ctmpack` keys the cache on subject/types/method/level only and returns the
  cached pack before `external_svg` is looked at. Pass `recache=True` with
  `overlay_file`. For a subject shared between projects (fsaverage!) that rewrites
  *their* cache too — move `<filestore>/<subject>/cache/<subject>_[*` aside before the
  build and back after (`try/finally`).
- **The browser caches the bundle's `<subject>_[inflated]_*.svg` / `.ctm` across
  rebuilds.** Same URL, fetched by XHR (a hard reload does *not* bypass it), so a stale
  overlay makes a rebuild look like it did nothing. Verify from a fresh origin (another
  port) or serve with `Cache-Control: no-store`; `performance.getEntriesByType('resource')`
  showing `transferSize: 0` confirms a cache hit.

`curvature_brightness=0.62, curvature_contrast=0.28, curvature_smoothness=2.0` flattens
the default near-binary curvature into a background that orients without competing with
the data, and `surface_specularity=0.1` kills the glare highlights that read as data.

## Getting a real colorbar next to a blend_curvature map

`Vertex2D` against a 2D `*_alpha` colormap keeps `vmin`/`vmax`/`cmap` live so pycortex
draws its own colorbar — but the shader-side blend looks washed out, pycortex ships only
~15 `*_alpha` maps, and datasets sharing one alpha mask collide in `Package.reorder`
(same `TypeError` as above). **Better: keep `blend_curvature` and draw the legend
yourself** from the ranges you already hold, as CSS gradients injected into the page.
Track the active dataset by wrapping `mriview.Viewer.prototype.setData` (the single
funnel every switch goes through), and probe the implicit global `figure` for the dataset
pycortex selects during load, before the wrapper can be installed.

## ROIs without Inkscape: `overlays.svg` paths from a vertex mask

You can contour any vertex mask in flatmap space and write real pycortex ROIs — no
tracing, ~2 s per subject, Dice ≈ 0.98 against the source mask. Full recipe and traps:
[`references/roi_authoring.md`](./references/roi_authoring.md). The traps, so you know
what you are walking into: the `rois > shapes > <g>` hierarchy is load-bearing and yields
zero ROIs silently if you get it wrong; `get_overlay()` with default args can rewrite the
file and eat your paths; restoring `overlays.svg` from a backup makes the next call block
on an `overwrite?` stdin prompt forever; the viewer labels every *path*, so a ragged mask
becomes a wall of labels; a few-mm marker cannot be contoured at all (draw a circle); the
Inkscape probe ignores `options.cfg`; and the overlay is cached next to the `.ctm`, so
edits do not reach a bundle until you clear the cache.

## Driving the static viewer from JavaScript

Everything the viewer can do is reachable from the page — that is how you give a bundle
its own UI (map buttons, legend, opening view) and how you check a build from a
browser-automation session.

```js
viewer.ui.set('mix', 0.5);               // 0 fiducial, 0.5 inflated, 1 flat
viewer.ui.set('camera.azimuth', 180);    // 180 from behind, 270 right hemisphere
viewer.ui.set('camera.altitude', 50);    // 90 level, 0.1 straight down (flatmaps)
viewer.ui.set('camera.radius', 215);     // fsaverage ~215, a native surface ~330
viewer.schedule();                       // repaint after ui.set
viewer.setData('Preferred numerosity');  // by dataset name
viewer.addEventListener('setData', e => console.log(e.name));
viewer.loaded.done(() => { /* surfaces are in */ });
```

**`viewer.animate([...])` freezes half-way in a background tab or an off-screen iframe.**
It interpolates on animation frames, which the browser throttles to nothing when the page
is not visible, so an opening view lands at whatever fraction it got to (azimuth 111
instead of 180). Animate for the look of it, then snap to the final state with `ui.set` +
`schedule()` after a timeout.

The page's globals are `viewer`, `figure` and `dataviews` (assigned in `static.html`'s
`onload`), and `window.self !== window.top` is the cheapest "am I in an iframe" test —
use it to hide your own panel and pycortex's `.dg` control box in an embedded copy.

## Copy-pasteable

- [`references/autoflatten.md`](./references/autoflatten.md) — cutting and flattening a
  whole cohort (cluster recipe, FS_LICENSE, the XLA-flag abort, which recon to flatten).
- [`references/roi_authoring.md`](./references/roi_authoring.md) — writing ROIs into
  `overlays.svg` from a vertex mask, with all seven traps.
- [`references/persistent_webshow.py`](./references/persistent_webshow.py) — a launch
  pattern that survives the daemon-thread exit and the hostname URL.
- [`references/static_bundle_with_legend.py`](./references/static_bundle_with_legend.py)
  — `make_static` plus an injected, dataset-tracking colorbar panel, a landing page and a
  server. Its docstring predates the `overlay_file`/recache and browser-cache traps above.
