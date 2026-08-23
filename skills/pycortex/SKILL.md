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

**0. An AI assistant driving these sessions cannot see `cortex.webgl.show()` —
render a static PNG and actually look at it before reporting anything.**

`cortex.webgl.show()` opens an interactive WebGL session in the *user's*
browser; nothing about it is inspectable from the process that launched
it. It is entirely possible for a script to run cleanly, print plausible
summary statistics (an `n=`, a threshold, a percentage), and still have
produced a dataset that renders as a **blank curvature-only image** —
e.g. because nothing survived a significance threshold, so `alpha` is 0
everywhere. The printed numbers alone will not catch this. Render the
same data with `cortex.quickflat.make_figure(vtx, with_curvature=True) →
fig.savefig(...)` (or this project's own `--static-png` flag where
available) and actually view the resulting file before describing the
result to anyone. This caught a genuinely broken figure in the
abstract_values session that spawned this skill — the printed log looked
completely normal.

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

**4. A freshly-`freesurfer.import_subj()`-ed pycortex subject has NO flat
map — `cortex.quickflat.make_figure()` (and any `Vertex.blend_curvature()`
static PNG) will hard-crash with `OSError` / `KeyError: 'flat'`.**

Flat maps are not derived automatically from the FreeSurfer surfaces —
they require a set of manual topological cuts (drawn in Freeview) that
`mris_flatten` then relaxes into 2D. `import_subj()` only imports the
fiducial/inflated/white/pial surfaces; nothing about it produces a
`flat_{hemi}.gii`. Symptom, traced end-to-end on abstract_values sub-25/26
(freshly ingested, never manually cut):

```
File ".../cortex/quickflat/utils.py", line 360, in _make_flatmask
    pts, polys = db.get_surf(subject, "flat", merge=True, nudge=True)
File ".../cortex/database.py", line 526, in get_surf
    fnm = str(os.path.splitext(files[type][hemi])[0])
KeyError: 'flat'
```

If the subject has never been manually cut, **don't try to route around
this with a curvature-only quickflat render as a silent substitute** — it
quietly produces a *different, weaker* deliverable (no flat unfolding) than
what was asked for. Two real options:

- **No flat map available yet**: fall back to inflated-surface static
  renders instead (`nilearn.plotting.plot_surf_stat_map` straight off the
  FreeSurfer `{hemi}.inflated` + `{hemi}.curv` files — no pycortex flat
  cut needed, works headlessly). Say explicitly that this is inflated, not
  flattened, and why.
- **Generate the flat map automatically** — see below.

### Auto-generating flat maps with `autoflatten` (no manual Freeview cutting)

[`gallantlab/autoflatten`](https://github.com/gallantlab/autoflatten) (`pip install
autoflatten`, **own conda env** — pulls its own jax/jaxlib, don't mix with a project's
TF/JAX env) maps a template cut set (derived from pycortex's own fsaverage cuts) onto a
subject via `mri_label2label`, then flattens with a JAX solver (`pyflatten`, the default
backend — no FreeSurfer `mris_flatten` needed, only the cut *projection* does). One
command per subject, budget real time for it (~11–12 min/hemisphere on ~150k vertices;
`--parallel` runs both concurrently for roughly single-hemisphere wall time) — submit via
`sbatch`/`srun`, not the login node:

```bash
autoflatten $SUBJECTS_DIR/sub-25_ses-1 --parallel --overwrite
```

Its output filename (`{hemi}.autoflatten.flat.patch.3d`) matches pycortex's naming
convention — but **`import_flat`'s own `patch` arg already appends `.flat` internally**
(`get_surf(..., patch+".flat")`), so pass `patch="autoflatten"`, NOT `"autoflatten.flat"`
— the doubled form silently looks for a nonexistent `....flat.flat.patch.3d` and raises
`FileNotFoundError`. Import directly (in the `pycortex2` env; rule 3 still applies):

```python
from cortex import freesurfer
freesurfer.import_flat(fs_subject, patch="autoflatten", hemis=["lh", "rh"],
    cx_subject=cx_subject, freesurfer_subject_dir=fs_subjects_dir,
    auto_overwrite=True)   # or it blocks on an input() prompt
```
Confirmed working end-to-end on abstract_values sub-25 (saves to
`<filestore>/<cx_subject>/surfaces/flat_{hemi}.gii`).

**Only two FreeSurfer binaries needed — `mri_info` and `mri_label2label`** (`mris_flatten`
is only for the alternate `--backend freesurfer`). On sciencecluster there's no bare-metal
FreeSurfer, but fmriprep's apptainer image is an *extracted sandbox dir*, not a `.sif`, so
its bundled binaries run directly, no `apptainer exec` needed:

```bash
export FREESURFER_HOME=/shares/zne.uzh/containers/fmriprep-25.2.3/opt/freesurfer
export PATH=$FREESURFER_HOME/bin:$PATH
export FS_LICENSE=$HOME/freesurfer/license.txt   # required — see gotcha below
export SUBJECTS_DIR=/shares/zne.uzh/gdehol/ds-abstractvalue/derivatives/fmriprep/sourcedata/freesurfer  # must contain fsaverage (template cut source)
```

**Missing `FS_LICENSE` fails silently, several steps away from the real error.**
`mri_info --version` needs no license and reports fine — false confidence that FreeSurfer
"works." But `mri_label2label` (the actual projection) does need one; the container's
FreeSurfer has no `opt/freesurfer/.license` (fmriprep normally supplies this via
`APPTAINERENV_FS_LICENSE` *through* apptainer, which doesn't apply when calling the
extracted binary directly). Without it, every cut — including the medial wall — silently
maps to 0 vertices, so the patch keeps the full closed surface, and flattening then dies
with an unrelated-looking `TopologyError: Euler characteristic χ = 2, expected 1`. Set
`FS_LICENSE` explicitly before running anything beyond a bare `--version` check.

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

**`quickflat.make_figure(..., with_colorbar=True)` on a `blend_curvature()`-baked
image draws a colorbar, but not YOUR colorbar.** Since the data+curvature are
already pre-blended into one flat RGB image, there's no live `vmin`/`vmax`/`cmap`
left for pycortex to introspect — it silently falls back to some default
scale (observed: `0–255` with a generic viridis-like swatch) that has nothing
to do with your actual data range. This doesn't error, so it's easy to publish
a mislabeled figure. Pass `with_colorbar=False` and annotate the real
`vmin`/`vmax`/`cmap` as text (title/caption) instead — or build a matching
colorbar separately, as this project's `visualize_subject_model.py
save_colorbar_pdf()` already does.

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
