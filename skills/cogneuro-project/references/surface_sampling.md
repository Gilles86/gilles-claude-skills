# Volume → fsnative → fsaverage sampling

A standard task in these projects: take a per-voxel quantity computed in
T1w-anat space (PRF parameters, GLM betas, decoding R², ROI maps) and
project it onto the cortical surface — first the subject's own fsnative
mesh, then optionally registered to fsaverage for cross-subject group
visualisation in pycortex.

This is the recipe distilled from `abstract_values/surface/sampling.py`.
The same pattern works for neural_priors, retsupp, retinonumeral —
file paths and the FreeSurfer subject naming differ but the moving
parts are identical.

## The two-step pipeline

### Step 1: T1w volume → fsnative `.func.gii`

```python
from nilearn import surface

data = surface.vol_to_surf(
    vol_path,                # T1w-space NIfTI
    str(pial),               # fsnative pial surface
    inner_mesh=str(white),   # fsnative white surface
)
```

The `inner_mesh=white` is the important part. nilearn samples along the
normal from pial to white at several depths and averages, which keeps
the signal *inside grey matter* and avoids leakage from CSF (pial-only
sampling) or white matter (white-only sampling).

Save as a GIfTI with one DataArray of float32:

```python
import nibabel as nib
im = nib.gifti.GiftiImage(darrays=[nib.gifti.GiftiDataArray(data.astype(np.float32))])
nib.save(im, str(out_fsnative_path))
```

### Step 2: fsnative `.func.gii` → fsaverage `.func.gii`

Uses FreeSurfer's `mri_surf2surf` via nipype.

> **FreeSurfer on the cluster.** The project conda envs don't ship
> FreeSurfer. On UZH sciencecluster, the binaries inside the unpacked
> fmriprep container run natively against the host glibc — no
> `apptainer exec` wrapper needed. Set:
>
> ```bash
> export FREESURFER_HOME=/shares/zne.uzh/containers/fmriprep-25.2.5/opt/freesurfer
> export PATH=$FREESURFER_HOME/bin:$PATH
> export FS_LICENSE=/shares/zne.uzh/containers/freesurfer/license.txt
> ```
>
> See the **sciencecluster** skill (`Containers ▸ Reusing
> container-bundled binaries from the host`) for the broader pattern.
>
> **And use `srun`, not the login node.** The sampling step itself is
> cheap (~5–10 s per (subject, model, hemi) pair on one CPU), but
> doing 8 subjects × 3 models × 2 hemis × 2 ops still runs ~2 minutes
> of CPU. Wrap it:
>
> ```bash
> srun --account=zne.uzh -c 2 --mem 8G --time 30 \
>     bash -lc 'source ~/data/miniforge3/etc/profile.d/conda.sh && \
>               conda activate <project> && \
>               export FREESURFER_HOME=/shares/zne.uzh/containers/fmriprep-25.2.5/opt/freesurfer && \
>               export PATH=$FREESURFER_HOME/bin:$PATH && \
>               python -m <package>.surface.sample_r2_to_surface \
>                       --bids-folder /shares/zne.uzh/gdehol/ds-<project>'
> ```



```python
import os
from nipype.interfaces.freesurfer import SurfaceTransform

os.environ["SUBJECTS_DIR"] = str(subjects_dir)  # nipype requires this
sxfm = SurfaceTransform(subjects_dir=str(subjects_dir))
sxfm.inputs.source_file = str(fsnative_path)
sxfm.inputs.out_file = str(fsaverage_path)
sxfm.inputs.source_subject = fs_subject       # subject's freesurfer dir name
sxfm.inputs.target_subject = "fsaverage"
sxfm.inputs.hemi = "lh"                       # or "rh"
sxfm.run()
```

The cluster apptainer fmriprep image ships fsaverage in its templateflow,
so it lives at `subjects_dir/fsaverage/` and SurfaceTransform finds it
without setup. If you ever run this off-cluster you may need to copy
the fsaverage subject into your local `SUBJECTS_DIR`.

## File naming convention

Inputs are T1w-space NIfTIs with BIDS entities, e.g.
`sub-XX_task-Y_space-T1w_desc-r2_pe.nii.gz`.

Surface outputs follow the same stem with two changes:

- Insert `_hemi-{L,R}` before `_space-`.
- Replace `_space-T1w` with `_space-fsnative` (or `_space-fsaverage`).
- Change extension to `.func.gii`.

So `sub-XX_..._space-T1w_desc-r2_pe.nii.gz` becomes
`sub-XX_..._hemi-L_space-fsnative_desc-r2_pe.func.gii` and
`sub-XX_..._hemi-L_space-fsaverage_desc-r2_pe.func.gii`.

Outputs live in the **same directory** as the input volume (the
encoding-model output dir, e.g. `derivatives/encoding_models/aprf/sub-XX/func/`).
Don't move them to a separate `surface/` tree — colocation with the
NIfTI keeps the BIDS sidecar logic intact and avoids hunt-and-peck later.

## fmriprep surface conventions to remember

- **Pial / white meshes per session.** fmriprep writes anat under
  `derivatives/fmriprep/sub-XX/ses-N/anat/` (one canonical session,
  usually `ses-1` for this project's multi-session subjects). Files are
  `sub-XX_ses-N_hemi-{L,R}_{pial,white}.surf.gii`. Pass these to
  `vol_to_surf`.
- **FreeSurfer subject is *per session*.** fmriprep creates its
  FreeSurfer stream as `sub-XX_ses-N` (with the session suffix), not
  `sub-XX`. SurfaceTransform's `source_subject` needs that exact name.
- **subjects_dir is `derivatives/fmriprep/sourcedata/freesurfer/`.**
  Lives alongside the BIDS-style fmriprep outputs.

## Pycortex subjects

- Per-subject: this project uses `abstractvalue.sub-XX` (the project-prefixed
  naming convention pycortex stores in `~/.config/pycortex/pycortex2/db/`).
  Used by `visualize_subject_model.py` for single-subject viewing.
- Group / template: `fsaverage` (pycortex's default). Used by
  `visualize_mean_r2_fsaverage.py`. fsaverage lives in pycortex's
  filestore and is shipped with the package.

## Pycortex viewer pattern with alpha masking

The viewer call pattern used across these projects:

```python
import cortex
from scipy.stats import norm

# Soft alpha: vertices below threshold fade smoothly via Gaussian CDF
# rather than being binary-masked. Looks cleaner on inflated brains.
def soft_alpha(values, thr, sigma):
    return norm.cdf(values, loc=thr, scale=sigma).astype(np.float32)

alpha = soft_alpha(r2, thr=2.0, sigma=1.0)            # in PERCENT
v = cortex.Vertex(np.nan_to_num(values).astype(np.float32),
                  pycortex_subject, vmin=thr, vmax=vmax, cmap="hot")
ds = {"label": v.blend_curvature(alpha)}              # ← blends with curv
cortex.webgl.show(ds)
```

`blend_curvature(alpha)` blends the colored layer onto the curvature
underlay using `alpha` as a soft mask — the cortex peeks through where
signal is weak.

**Units.** GLMsingle and the encoding-model fitter store R² as
**percent (0–100)**, not fraction. Pick thresholds accordingly
(`thr=2` means 2%, not 2× variance).

## See also

- `abstract_values/surface/sampling.py` — the helper module that wraps
  this recipe. Other projects can copy it almost verbatim.
- `abstract_values/surface/sample_r2_to_surface.py` — multi-subject driver.
- `abstract_values/visualize/visualize_mean_r2_fsaverage.py` — group viewer.
- `abstract_values/surface/sample_aprf_to_surface.py` — older single-subject
  variant that samples all aPRF parameters (mu, sd, ...) and optionally
  the gabor R². Worth porting onto the helpers above next time it's touched.
