# Defacing — with a QC gate that looks at pixels

Defacing is the hard gate before anything leaves the machine. Two lessons
from doing it twice: (1) far more volumes bear a face than the raw `anat/`
folder, and (2) a JSON `"Defaced": true` flag written by the defacing script
proves nothing — only the voxels do.

## Which volumes bear a face

| Location | Files | Action |
|---|---|---|
| Raw `anat/` | `*_T1w`, `*_T2w`, `*_FLAIR`, `*_PDw`, `*_angio`, `*_inplaneT*` | deface |
| fMRIPrep `anat/` | `*_desc-preproc_T1w.nii.gz` (not skull-stripped), `*_desc-preproc_T2w`, MNI-space `space-MNI*_desc-preproc_T1w` | deface or drop |
| FreeSurfer `mri/` | `orig/*.mgz`, `orig.mgz`, `rawavg.mgz`, `nu.mgz`, `orig_nu.mgz`, `T1.mgz`; check `norm.mgz` | drop (or deface via the raw mask) |
| FreeSurfer head surfaces | `surf/*.seghead`, `*.head`, `mri/seghead.mgz`, `bem/` | drop |
| Reports | MRIQC T1w HTML (mosaics), fMRIPrep `sub-XX.html` + `sub-XX/figures/*.svg` (anatomical reportlets show head slices) | drop; regenerable |
| pycortex subject DB | `anatomicals/raw.nii.gz` | never ship |
| Low-res EPI: BOLD, `boldref`, `sbref`, fieldmaps | 2–3 mm, face not recognisable | conventionally **not** defaced; OpenNeuro accepts |

Two T1w "runs" in one session are often two **reconstructions of the same
scan** (identical affine, different intensity scaling). Both carry the face;
both get defaced. Because the affine is identical, one registration serves
both (see `--applyto` below) — assert identical shape and affine first.

## Workflow: SOURCE → WORK → TARGET

```
SOURCE (canonical, read-only)
   │  stage: header text cleared, gzipped, voxels byte-identical
   ▼
WORK/undefaced/…          ← never uploaded; delete after publication
   │  pydeface → WORK/pydeface/…_defaced.nii.gz   (used only as a MASK)
   │  mask = (undefaced != 0) & (defaced == 0)    (or pydeface's warped mask, --nocleanup)
   │  apply mask at raw-voxel level → verify → metrics → PNG report
   ▼
WORK/qc/{metrics.tsv, index.html, *.png}  → human approves every image → qc_approved.tsv
   │  copy-to-TARGET step refuses anything not in qc_approved.tsv
   ▼
TARGET (upload tree): defaced anatomicals only
```

The **risk_experiment way** — pydeface in place on the dataset, then a check
that reads the JSON flag — is what not to do: it mutates the canonical copy,
it cannot be verified after the fact (the original is gone), and the check
never opens the image.

## Apply the mask yourself, at the raw-voxel level

pydeface's own output is written through a nibabel round-trip: dtype may
become float, `scl_slope/inter` change or vanish, header text fields are
rewritten. You then cannot prove the released image equals the original
except for the face. So treat pydeface's output as a **mask only**:

1. Read the staged undefaced image's raw bytes; parse the 348-byte header.
2. Zero the masked voxels **in the stored datatype** (`dataobj.get_unscaled()`,
   not `get_fdata()`).
3. Write header (text fields already blank) + extensions + new voxel block,
   byte-for-byte otherwise.
4. **Verify** against the undefaced copy: same shape, dtype, qform, sform,
   `scl_slope/inter`; kept voxels identical; removed voxels all zero.

Template: [`deface_apply_qc.py`](deface_apply_qc.py) — plain Python +
nibabel, no project code, usable from any lab's tree. The same function
applies one mask to the sibling reconstruction. Doing it in MATLAB is
possible (`niftiread`/`niftiwrite` with the *original* `info` struct, or
`spm_vol`/`spm_read_vols`/`spm_write_vol`) but both paths tend to rewrite
`datatype`/`scl_slope`/`scl_inter` — if you go that way, the byte-level
verification step is not optional.

## Tools

- **pydeface** — `pip install pydeface`; needs FSL `flirt`. On a cluster
  without FSL, the official FSL conda channel ships it:
  ```yaml
  channels:
    - https://fsl.fmrib.ox.ac.uk/fsldownloads/fslconda/public/
    - conda-forge
  dependencies: [python=3.11, fsl-flirt, fsl-avwutils, nibabel, numpy, scipy, matplotlib, pip, {pip: [pydeface, nitransforms]}]
  ```
  ~1–2 min per image; run as a cluster array over images.
  `pydeface in.nii.gz --outfile out_defaced.nii.gz --force`;
  `--applyto sibling.nii.gz` applies the same warped mask to other images in
  the same space; `--nocleanup` keeps the warped mask file.
- **AFNI** `@afni_refacer_run -mode_deface -input in.nii.gz -prefix out` —
  good fallback when pydeface's registration fails (odd FOV, neck included).
  `-mode_reface` replaces rather than removes; OpenNeuro accepts either.
- **FreeSurfer** `mri_deface` — older, still works.

Use one tool for the whole dataset; record tool + version in the sidecar. If
a fallback was needed for some images, record which.

## QC gate

### Automated metrics (per image; template computes them)

| Metric | Definition | Flag when |
|---|---|---|
| `frac_head_removed` | removed voxels / head voxels (head = intensity above Otsu or a robust percentile of nonzero) | < 0.02 (face still there / registration failed) or > 0.35 (over-aggressive) |
| `brain_removed` | removed voxels inside the brain mask | **≠ 0 → reject** |
| `brain_removed_dilated` | removed voxels inside a 3-voxel-dilated brain mask | > 0 → look closely |
| `verify_ok` | byte-level verification passed | not True → reject |

**Getting the brain mask into the raw T1w grid.** fMRIPrep's
`desc-brain_mask` is in preproc-T1w space, which is *not* the raw grid
(reoriented, resampled, averaged over T1ws). Per input T1w fMRIPrep writes
`…_from-orig_to-T1w_mode-image_xfm.txt` (ITK affine) when more than one T1w
was averaged; apply its **inverse** to bring the mask to the raw grid
(`nitransforms.linear.load(xfm, fmt='itk')`). Then **sanity-check the
direction**: resample the raw T1w into the preproc grid with the same
transform and correlate with `desc-preproc_T1w` — r > 0.9 means the direction
is right; r near 0 means invert. With a single T1w and no xfm file, the
grids often still differ by a conform step; use header-based resampling
(`nilearn.image.resample_to_img(mask, raw, interpolation='nearest')`) after
checking the sforms describe the same world space.

### Visual report — a human looks at EVERY image

One PNG per image, before/after side by side:

- **Sagittal maximum-intensity projection** — the profile silhouette. Nose,
  lips, chin gone? Eyes gone?
- **Coronal MIP** — the frontal silhouette. Symmetric removal? One side left?
- **Mid-sagittal slice** with the removed region overlaid in colour — shows
  where the cut runs relative to the frontal pole and cerebellum.
- **Axial slice through the orbits.**

An `index.html` listing all PNGs with the metrics next to each; scroll
through all of them; record approvals in `qc_approved.tsv`
(`path, approved, approver, date, note`). Rejected images get redone
(different tool, `robustfov` neck crop first, different `--cost`) and
re-reviewed. The step that copies into `TARGET` reads `qc_approved.tsv` and
refuses anything absent — that is the gate.

Things you will see: ears left in place (fine), a thin skin rim over the
forehead (fine), an eye still visible (reject), the frontal or temporal pole
clipped (reject), a lateral offset leaving half the face (reject —
registration failed).

## FreeSurfer volumes kept in a derivatives release

Don't trust a memorised list; check each kept volume: count nonzero voxels
**outside a dilated `brainmask.mgz`** — must be ~0. Skull-stripped candidates:
`brainmask.mgz`, `brain.mgz`, `brain.finalsurfs.mgz`, `aseg.mgz`,
`aparc+aseg.mgz`, `aparc.a2009s+aseg.mgz`, `wm.mgz`, `filled.mgz`,
`ribbon.mgz`, `wmparc.mgz`. Full-head (drop): `orig/*`, `orig.mgz`,
`rawavg.mgz`, `nu.mgz`, `orig_nu.mgz`, `T1.mgz`. Surfaces (`?h.white`,
`?h.pial`, `?h.inflated`, `?h.sphere*`, labels, annots) carry no face — but
their file headers carry a "created by <user> on <date>" stamp (see
[`deidentification.md`](deidentification.md)).

## Sidecar, after the checks

Only once verification and visual approval pass:

```json
{"Defaced": true,
 "DefacingMethod": "pydeface <ver> (FSL flirt <ver>); mask applied at voxel level to the original image; verified voxel-identical outside the mask; visually QC-approved"}
```

## Final guard on the upload tree

```bash
find <TARGET> \( -name '*T1w*' -o -name '*T2w*' -o -name '*FLAIR*' -o -name '*.mgz' \) -type f | sort > /tmp/highres.txt
# every path must be in qc_approved.tsv (or be a skull-stripped derivative that passed the outside-brain check)
```

The identifier audit ([`identifier_audit.py`](identifier_audit.py)) does the
same by geometry — every 3D volume with sub-1.5 mm voxels must be on the
approved list — so a mis-named anatomical cannot slip through.
