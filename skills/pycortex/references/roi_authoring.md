# ROIs without Inkscape: generating `overlays.svg` paths from a vertex mask

Read this before writing anything into a subject's `overlays.svg`. Seven traps, all
silent or reported far from their cause.

Pycortex ROIs are vector paths in the subject's `overlays.svg`, and the documented way
to make them is to trace by hand in Inkscape. You do not have to. If you already have
the ROI as a **vertex mask** — a FreeSurfer annotation, an atlas label, a thresholded
map — you can contour it in flatmap space and write the paths yourself, in about two
seconds per subject. The result is a real ROI: `get_roi_verts()` finds it, and the webgl
viewer draws it on top of every map.

Needs flat surfaces: `overlays.svg` lives in flatmap coordinates, so a subject that has
not been cut or auto-flattened cannot get one (see `autoflatten.md`).

Verified end to end: Dice between the mask recovered from the SVG and the annotation it
came from was 0.975 (IPS), 0.991 (lateral occipital), 0.953 (BA4a+BA4p) on abstract_values,
and 0.98–0.99 for NPC1/NPC2 across 35 tms_risk subjects. The shortfall is contour
discretisation, not misregistration.

## Recipe

1. Flat coordinates → SVG pixel space, the same normalisation `SVGOverlay.set_coords`
   uses:
   ```python
   pts, _ = cortex.db.get_surf(subject, "flat", merge=True, nudge=True)
   c = pts[:, :2].astype(float); c -= c.min(0); c /= c.max(0)
   svg_xy = c * svgshape          # (width, height) from the <svg> header
   ```
2. Rasterise the mask onto a grid over that space by nearest surface vertex (`cKDTree`),
   blur it a little (a couple of cells; the 0.5 level of a blurred binary mask stays put
   but loses the staircase), then `plt.contour(..., levels=[0.5])`. A 450–1200-wide grid
   is plenty for an outline. Contour each hemisphere separately, or a region touching the
   medial edge bridges across the gap between the two flatmaps.
3. **Flip y** when emitting path data (`y -> height - y`): SVG y grows downward, flat y
   grows upward. A wrong flip still parses and still looks like a plausible ROI — it is
   mirrored. Dice against the source mask is the only honest check.
4. Write the paths into the right place (trap 1) and stroke them with `fill:none`.

**Reading them back:**
```python
ov = cortex.db.get_overlay(subject, modify_svg_file=False)
idx = np.asarray(ov.rois.get_mask("IPS"), dtype=int)  # vertex INDICES, not a boolean mask
```
`get_mask` returns indices, so build the boolean yourself before comparing — otherwise
the shapes will not broadcast against a per-vertex array. Keep the `dtype=int`: an ROI
whose paths all got dropped returns `[]`, which numpy makes `float64`, and
`m[np.asarray([])] = True` dies with `IndexError: arrays used as indices must be of
integer (or boolean) type` — a confusing way to learn that one ROI came out empty.

## Traps

**Trap 1 — the hierarchy is load-bearing and failure is silent.**
`Overlay.__init__` reads `_find_layer(layer, "shapes").findall("g")`, so the structure
must be

```
<g inkscape:label="rois" inkscape:groupmode="layer">
  <g inkscape:label="shapes" inkscape:groupmode="layer">
    <g inkscape:label="IPS" id="roi_IPS">      <!-- one group per ROI -->
      <path d="M ... Z" style="fill:none;stroke:#3B5BA5"/>
    </g>
```

A labelled `<path>` placed directly in the `rois` layer is valid XML, loads without an
error, and yields **zero** ROIs — `ov.rois.shapes` is simply empty.

**Trap 2 — `cortex.db.get_overlay()` can eat your edits.** With default arguments it
regenerates the image layers and may rewrite `overlays.svg` from its own in-memory tree,
discarding paths added underneath it. Keep it out of the writer entirely: read `svgshape`
from the SVG header yourself (`root.get("width")/get("height")`), and when you must load
an overlay to check your work, pass `modify_svg_file=False`.

**Trap 3 — never restore `overlays.svg` behind pycortex's back.** Copying a backup over
that file makes the next pycortex call prompt `overwrite overlays.svg? (y/n [n])` **on
stdin**, which blocks forever in a script or a background task — and looks exactly like a
slow computation. Every "hang" in a full day of this was that prompt; the actual work
takes seconds. Make the writer idempotent (strip stray paths, replace the groups) so
there is nothing to restore.

**Trap 4 — one label per PATH, so a ragged mask becomes a wall of labels.** The viewer
writes the ROI name next to every path in the group, not once per ROI. A volume-defined
mask sampled to the surface easily contours into six pieces, and the viewer then stacks
six copies of the name on top of each other. Keep only the pieces that matter — drop any
contour below a fraction (~0.25) of the largest by polygon area:

```python
area = [0.5 * abs(np.dot(s[:, 0], np.roll(s[:, 1], 1)) -
                  np.dot(s[:, 1], np.roll(s[:, 0], 1))) for s in segs]
segs = [s for s, a in zip(segs, area) if a >= 0.25 * max(area)]
```

and budget about three ROIs per viewer — beyond that the labels, not the map, are what
the reader sees.

**Trap 5 — a few-mm marker cannot be contoured; draw the circle yourself.** A 3 mm disc
is a handful of raster cells, and the Gaussian blur that de-staircases a real ROI shrinks
it to a sliver or to nothing (observed: Dice 0.13 against the source disc on one subject,
zero paths on another, and the flatmap's local scaling makes it unpredictable). For a
point marker — a stimulation site, a peak vertex — emit a polygon circle in SVG space
instead of contouring:

```python
pts = svg_xy[mask]                       # mask = vertices within a few mm
c = pts.mean(0)
r = max(3.0, np.linalg.norm(pts - c, axis=1).max())
t = np.linspace(0, 2 * np.pi, 48, endpoint=False)
ring = np.column_stack([c[0] + r * np.cos(t), height - (c[1] + r * np.sin(t))])
```

Dice against the disc then lands at 0.7–0.9 (the circle circumscribes it), and it never
comes out empty.

**Trap 6 — the Inkscape version probe ignores your config.** Writing and reading ROIs
needs no binary — pycortex parses SVG paths in pure Python (`svgoverlay.COMMANDS`), so
`get_roi_verts` works without it. *Drawing* them does: `SVGOverlay.get_texture` shells
out to Inkscape to rasterise a layer, and that is what `quickflat(with_rois=True)` uses.
`cortex.testing_utils.inkscape_version()` calls `shutil.which('inkscape')`, so setting
`dependency_paths.inkscape` in `options.cfg` does nothing on its own: if the binary is
not on `PATH` under that exact name, `INKSCAPE_VERSION` stays `None` and ROI rendering
silently produces nothing. On macOS the app ships the CLI inside the bundle:

```bash
ln -sf /Applications/Inkscape.app/Contents/MacOS/inkscape ~/.local/bin/inkscape
```

**Trap 7 — the overlay SVG is cached next to the `.ctm`.** `make_static` only *copies*
the cached copy from the pycortex store, it never rebuilds it. ROIs added to
`overlays.svg` after the first bundle therefore never reach the viewer, and deleting the
SVG inside the bundle does not help — the stale cached one is copied again. Invalidate
the cache (which forces the `.ctm` to regenerate, ~1 min):

```python
cache = Path(cortex.database.default_filestore) / cx_subject / "cache"
if overlays_svg.stat().st_mtime > cached_svg.stat().st_mtime:
    for stale in cache.glob(f"{cx_subject}_[[]*"):
        stale.unlink()
```

## When the viewer still will not draw them

Burn the outlines into the data instead. `VertexRGB.red/green/blue` are `Vertex`
objects, so assign through `.data`:

```python
vtx.red.data[edge] = r; vtx.green.data[edge] = g; vtx.blue.data[edge] = b
```

Not toggleable, and it covers the vertices it paints, but it cannot fail to show — worth
having as a fallback while debugging the overlay path. Note pycortex forces ROI strokes
to **white** in the viewer (`rois_paths` style), so a white outline over a bright map is
invisible even when everything else is right; the burned-in version keeps whatever colour
you choose.

A worked implementation (contouring, circles, prune, read-back Dice, cache clearing) is
`tms_risk/visualize/roi_overlays.py`.
