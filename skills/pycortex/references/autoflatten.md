# Auto-generating flat maps with `autoflatten` (no manual Freeview cutting)

Read this before flattening anything. A freshly `import_subj()`-ed pycortex subject has
no flat map at all, and every failure mode below is silent or reports something unrelated.

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
`FileNotFoundError`. Import directly (in the `pycortex2` env; golden rule 3 still
applies):

```python
from cortex import freesurfer
freesurfer.import_flat(fs_subject, patch="autoflatten", hemis=["lh", "rh"],
    cx_subject=cx_subject, freesurfer_subject_dir=fs_subjects_dir,
    auto_overwrite=True)   # or it blocks on an input() prompt
```
Confirmed working end-to-end on abstract_values sub-25 and on all 35 tms_risk subjects
(saves to `<filestore>/<cx_subject>/surfaces/flat_{hemi}.gii`).

**Only two FreeSurfer binaries needed — `mri_info` and `mri_label2label`** (`mris_flatten`
is only for the alternate `--backend freesurfer`). On sciencecluster there's no bare-metal
FreeSurfer, but fmriprep's apptainer image is an *extracted sandbox dir*, not a `.sif`, so
its bundled binaries run directly, no `apptainer exec` needed:

```bash
export FREESURFER_HOME=/shares/zne.uzh/containers/fmriprep-25.2.3/opt/freesurfer
export PATH=$FREESURFER_HOME/bin:$PATH
export FS_LICENSE=$HOME/freesurfer/license.txt   # required — see gotcha below
export SUBJECTS_DIR=<dir with the subjects AND fsaverage>   # fsaverage = template cut source
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

**`BrokenProcessPool` right after a successful projection = the XLA flag, not memory.**
`autoflatten.flatten.threading.configure_threading(n)` appends
`--xla_cpu_multi_thread_eigen_thread_count=n` to `XLA_FLAGS` whenever a core count is
given (`--n-cores`, or `--parallel` splitting cores between hemispheres). jaxlib ≥ 0.11
does not know that flag and **aborts the process** (`F... Unknown flag in XLA_FLAGS`),
which the parent only sees as

```
concurrent.futures.process.BrokenProcessPool: A process in the process pool was terminated abruptly
```

after the projection step has already written `{hemi}.autoflatten.patch.3d`. MaxRSS is
~2 GB, so it looks nothing like an OOM. It cannot be fixed from the outside by
pre-setting `XLA_FLAGS` (the guard is a prefix match on the *same* flag name), so patch
the function in every process — pool workers included — with a `sitecustomize.py` on
`PYTHONPATH`:

```python
import os, autoflatten.flatten.threading as _t
_configure = _t.configure_threading
def configure_threading(n_threads=None):
    _configure(n_threads)
    os.environ['XLA_FLAGS'] = ' '.join(
        f for f in os.environ.get('XLA_FLAGS', '').split()
        if not f.startswith('--xla_cpu_multi_thread_eigen_thread_count'))
_t.configure_threading = configure_threading
```

**Whole-cohort flattening is a SLURM array job.** 35 subjects × `--cpus-per-task=8`,
`--mem=16G`, `--parallel`: 19–39 min each, all in one wave. What matters is *which*
reconstruction you flatten: the patch is only importable into the pycortex subject built
from the **same** recon (vertex counts must match — one tms_risk subject differed by 370
vertices between `derivatives/freesurfer` and `fmriprep/sourcedata/freesurfer`). If the
recon that pycortex used lives on your laptop, upload just what autoflatten reads —
`{lh,rh}.{white,pial,fiducial,smoothwm,inflated,sphere.reg,curv,sulc}`, ~60 MB/subject —
into a scratch `SUBJECTS_DIR`, and symlink `fsaverage` there from the container
(`$FREESURFER_HOME/subjects/fsaverage`) for the template cuts. Pull back only
`{lh,rh}.autoflatten.flat.patch.3d`. QC is free: each run writes
`{hemi}.autoflatten.flat.patch.png` with the metric distortion (~14 % mean, a handful of
flipped faces is normal).

A worked example of the whole loop — upload, array job, pull back, import — is
`tms_risk/surface/slurm_jobs/autoflatten.sh` plus
`tms_risk/visualize/import_flatmaps.py` in the tms_risk repo.
