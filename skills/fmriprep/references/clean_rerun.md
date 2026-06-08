# Forcing a true clean fmriprep rerun

The single most common fmriprep pitfall on our setup: a cancelled job
(scancel, walltime, node failure) silently resumes against partial nipype
cache on resubmission, exits **code 0**, finishes in **~30 min**, and
produces **broken outputs** (only `desc-preproc_T1w.nii.gz`, no freesurfer
dir, no segmentations, no surfaces). Downstream then fails confusingly
(neuropythy `StopIteration` on the missing cortical ribbon; GLMsingle /
mask-creation missing-file errors). Same mechanism makes a changed
`--bold2anat-init` silently have **no effect**. See SKILL.md for the full
story.

## Smell test — is the runtime suspicious?

| Subject sessions | Healthy runtime | Suspicious if |
| ---: | --- | --- |
| 1 | 2–3h | <1h |
| 2 | 5–6h | <2h |
| 3 | ~12h | <6h |

A re-run that finishes in 30 min + a downstream neuropythy `StopIteration`
== the cache was reused.

## The 3-path wipe

Wipe **all three** paths before resubmitting. Missing any one → fmriprep
finds leftover state and produces broken outputs again. The first two on
their own are **not** enough.

```bash
SUB=10                              # subject label, e.g. "10" or "pil02"
FMRIPREP_VER=25_2_wf                # match the apptainer image version
DERIV=/shares/zne.uzh/gdehol/ds-<project>/derivatives/fmriprep

# 1. nipype workflow scratch (the bind-mounted /workflow cache, ~10–15GB)
rm -rf /scratch/gdehol/fmriprep_${FMRIPREP_VER}/sub_${SUB}_ses_*_wf/

# 2. fmriprep derivatives + HTML sentinel
rm -rf "${DERIV}/sub-${SUB}/"
rm -f  "${DERIV}/sub-${SUB}.html"

# 3. freesurfer cache (under fmriprep sourcedata, NOT next to scratch)
rm -rf "${DERIV}/sourcedata/freesurfer/sub-${SUB}/"
```

If the wrapper is submitted via Snakemake, the rule won't re-run unless its
sentinel is gone too. Use `.fmriprep_done` (touched only after the
output-based success check — see `fmriprep.sh`) as the rule output, **not**
the HTML, which fmriprep writes on failure as well.

## "fmriprep just finished — is it real?" checklist

1. **Runtime** — see smell-test table above.
2. **`ses-*/anat/` file count** — a clean run has ~30+ files (transforms,
   segmentations, masks, surfaces); a cache-hit broken run has ~2.
   ```bash
   ls "${DERIV}/sub-${SUB}/ses-1/anat/" | wc -l
   ```
3. **freesurfer ribbon exists**:
   ```bash
   ls "${DERIV}/sourcedata/freesurfer/sub-${SUB}/mri/ribbon.mgz"
   ```
4. **HTML descriptive text** names the right `--bold2anat-init` target. If
   you forced `t1w` but it says `T2w`, the cache was reused.

If any of 1–3 fails, do the 3-path wipe and resubmit.
