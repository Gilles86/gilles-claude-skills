---
name: fmriprep
description: Operational knowledge for fmriprep on Gilles's projects — resources, the nipype `/scratch` cache trap, how to force a true clean rerun, why `--bold2anat-init` doesn't always take effect, HTML-report vs NIfTI ground truth, and visual coregistration QA. Use whenever submitting, debugging, or re-running fmriprep, or when fmriprep finishes suspiciously fast (<2h for a 2-session subject), or when downstream tools (neuropythy mask creation, GLMsingle) error on missing freesurfer / cortical ribbon files. Pairs with the **sciencecluster** skill (general SLURM ops) and **cogneuro-project** skill (where the wrapper script lives in the repo layout).
---

# fmriprep on Gilles's projects

Lessons distilled from re-running fmriprep across abstract_values,
neural_priors, retsupp, retinonumeral. The wrapper script lives at
`<project>/<package>/cluster_preproc/fmriprep.sh` (per the
**cogneuro-project** skill); this skill is about *what goes wrong with
fmriprep itself*.

For fmriprep's own docs (what it does, CLI flags, output spec), see
<https://fmriprep.org>. This skill assumes that baseline.

## Healthy resources

For 2-session subjects (`cluster_preproc/fmriprep.sh`):

| Setting | Value |
| --- | --- |
| CPUs | 16 |
| Memory | 64G |
| Walltime | 24h |
| Partition / QoS | `standard` / `normal` (24h cap) |
| Apptainer image | `/shares/zne.uzh/containers/fmriprep-<version>` |
| Output spaces | `T1w fsnative` |

Clean runtime on UZH sciencecluster: **~5–6h for 2-session subjects**
(~12h for 3-session). Anything substantially shorter is a smell.

For 3+ session subjects, bump to `standard` + `medium` qos (48h cap) and
~96G memory.

## The cache trap (most common pitfall)

fmriprep stores intermediate nipype workflow state at:

```
/scratch/<user>/fmriprep_<major>_<minor>_wf/sub_<XX>_ses_<X>-<Y>_wf/
```

This survives the SLURM job exit (it's a bind mount: the apptainer
`-B /scratch/<user>:/workflow` line in `fmriprep.sh`). Typical size
~10–15GB per subject.

**The problem:** if a fmriprep job is **cancelled mid-flight** (scancel,
walltime exceeded, node failure) and then **resubmitted**, fmriprep
silently resumes against the partial cached state. The new job:

- Exits with **code 0** (looks successful to SLURM and snakemake).
- Finishes in **~30 minutes** instead of ~5h.
- Produces **broken outputs**: only `desc-preproc_T1w.nii.gz` in
  `ses-1/anat`, no freesurfer dir, no segmentations, no surface files.

Downstream tools then fail in confusing ways:

- `neuropythy.freesurfer_subject(fs_dir)` →
  `StopIteration` (cortical ribbon file missing).
- GLMsingle / mask-creation scripts → missing-file errors.
- The SLURM-level failure looks unrelated to the fmriprep step.

### Smell test

| Subject sessions | Healthy fmriprep runtime | Suspicious if |
| ---: | --- | --- |
| 1 | 2–3h | <1h |
| 2 | 5–6h | <2h |
| 3 | ~12h | <6h |

If a re-run finishes in 30 min and downstream errors with neuropythy
`StopIteration` — the cache is the culprit.

### Forcing a true clean rerun

Wipe **all three** paths before resubmitting:

```bash
SUB=10                              # subject label, e.g. "10" or "pil02"
FMRIPREP_VER=25_2_wf                # match the apptainer image version
DERIV=/shares/zne.uzh/gdehol/ds-<project>/derivatives/fmriprep

# 1. nipype workflow scratch
rm -rf /scratch/<user>/fmriprep_${FMRIPREP_VER}/sub_${SUB}_ses_*_wf/

# 2. fmriprep derivatives + HTML sentinel
rm -rf "${DERIV}/sub-${SUB}/"
rm -f  "${DERIV}/sub-${SUB}.html"

# 3. freesurfer cache (lives under fmriprep sourcedata, NOT next to scratch)
rm -rf "${DERIV}/sourcedata/freesurfer/sub-${SUB}/"
```

Missing any of the three → fmriprep finds leftover state on the next
run and produces broken outputs again. The first two on their own are
not enough.

If the wrapper is submitted via snakemake, this also means **the rule
won't re-run unless the HTML sentinel is gone**. The HTML is what
snakemake checks to decide if fmriprep already "ran" for a subject.

## `--bold2anat-init` is cached too

If you re-run fmriprep with a different `BOLD2ANAT_INIT` value but
leave `/scratch` intact, the previously-computed BOLD↔T1w transform is
reused. The flag has **no effect**. Hints that this is happening:

- HTML report's descriptive text **still says** the old method (e.g.
  "The aligned T2w image was used for initial co-registration") even
  though the cmdline passed `--bold2anat-init t1w`.
- The runtime is too short (cache hit, see above).

Fix: same 3-path wipe procedure as the cache trap.

The fix commit in abstract_values that wired `BOLD2ANAT_INIT=t1w`:

- `abstract_values/snakemake/Snakefile`: passes `BOLD2ANAT_INIT=t1w`
  via env var to the wrapper script.
- `abstract_values/snakemake/config.yaml`: `bold2anat_init: "t1w"`.
- `ingest_new_session.sh`: passes `BOLD2ANAT_INIT=${BOLD2ANAT_INIT:-t1w}`
  to the sbatch.
- `cluster_preproc/fmriprep.sh`: appends `--bold2anat-init $BOLD2ANAT_INIT`
  to the apptainer command if the env var is set.

Default fmriprep behavior (`auto`) picks T2w when present, which has
historically given bad registration with our cross-session T2w
acquisitions.

## The html exists ≠ fmriprep succeeded

**Critical:** fmriprep writes `sub-<XX>.html` on **failure** too. The
report can be a *failure-summary* dumping the workflow exception, with
fmriprep itself raising and apptainer exiting non-zero. Both the
old `if apptainer_rc != 0 && [ -f html ]; then exit 0` fallback in
`fmriprep.sh` and a naive Snakemake rule `output: sub-<XX>.html` will
silently mark the rule as "done" in that case. Downstream rules then
fail trying to read missing preproc outputs (typical sub-12 /
3573299 case on 2026-05-29: ZRAN_READ_FAIL on a gzip workflow
intermediate, `fMRIPrep failed: 15 raised`, apptainer exit 1, html
written anyway, downstream mask creation broke with "missing
preproc_T2w in ses-2/anat").

The wrapper script *does* need an exit-1 tolerance branch — apptainer
≥ 1.4 has a known habit of returning 1 on otherwise-clean fmriprep
runs. But the discriminator must be **output-based, not html-based**:

```bash
APTAINER_RC=$?
APARCASEG="${DERIV}/sub-${SUB}/ses-1/anat/sub-${SUB}_ses-1_desc-aparcaseg_dseg.nii.gz"

if [[ $APTAINER_RC -ne 0 ]]; then
    if [[ -f "$APARCASEG" ]]; then
        echo "apptainer exit $APTAINER_RC tolerated — late-stage anat output present."
    else
        echo "apptainer exit $APTAINER_RC and late-stage anat missing — real failure."
        exit $APTAINER_RC
    fi
fi
```

`aparcaseg_dseg.nii.gz` is written by freesurfer's full autorecon. It
is present on truly-finished runs; absent on early failures (ZRAN,
fmap registration crash, etc.) where fmriprep raised before that
stage. For pilots with no ses-1 anat acquisition (rare), pick a
different stage-late output that matches.

In Snakemake, also pair this with a touch-sentinel rule output — see
the **snakemake** skill's [`references/orphaned_jobs.md`](../snakemake/references/orphaned_jobs.md)
and [`references/rule_output_changes.md`](../snakemake/references/rule_output_changes.md)
for why `output: ".fmriprep_done"` is better than `output: ".html"`.

## HTML report rendering

`sub-<XX>.html` is a small (~250KB) wrapper. The actual figures are
SVGs inside `sub-<XX>/figures/`. To render the report locally, sync
both — the standard `sync_fmriprep.sh` does that but the per-rule
rsync excludes can drop figures. Spot-check:

```bash
open .../derivatives/fmriprep/sub-<XX>.html
# If the page is mostly empty boxes, figures didn't sync.
```

The HTML SVGs are useful but can be **visually misleading** — they
flip between two states (boldref vs T1w), which can highlight tiny
offsets that don't matter functionally, or hide subtle ones that do.

**The most reliable visual QA** is to open the preprocessed T1w + a
T1w-space boldref in fsleyes and inspect alignment of the BOLD ribbon
to cortex:

```bash
fsleyes \
  .../derivatives/fmriprep/sub-<XX>/ses-1/anat/sub-<XX>_ses-1_desc-preproc_T1w.nii.gz \
  .../derivatives/fmriprep/sub-<XX>/ses-1/func/sub-<XX>_ses-1_task-<task>_run-1_space-T1w_boldref.nii.gz \
  --cmap hot --alpha 40
```

abstract_values has ready-made loops for this (worth porting to other
projects when the cross-project QA helper crystallizes):

- `abstract_values/visualize/inspect_coreg_fsleyes.py` — interactive
  fsleyes per (subject, session)
- `abstract_values/visualize/check_coreg.py` — batch nilearn
  `plot_anat().add_edges(boldref)` to per-subject PDF

## Where the logs are

Two submission paths, two log conventions:

| Submission path | Log file |
| --- | --- |
| Direct `sbatch fmriprep.sh` | `~/logs/<project>_fmriprep_<jobid>-<arrayidx>.txt` (from the `#SBATCH --output` in the wrapper) |
| `snakemake-executor-plugin-slurm` | `<workdir>/.snakemake/slurm_logs/rule_fmriprep/<XX>/<jobid>.log` (plugin overrides `--output`) |

When the snakemake driver is the orchestrator, do NOT waste time
grepping `~/logs/` — the logs are inside the working tree's
`.snakemake/`. This is especially confusing because the wrapper script
*has* a `#SBATCH --output=...` line; the plugin just ignores it.

## Quick checklist for a "fmriprep just finished — is it real?"

1. **Runtime**: see smell-test table above.
2. **`ses-*/anat/` count**: a clean run has ~30+ files (transforms,
   segmentations, masks, surfaces); a cache-hit broken run has ~2.
   ```bash
   ls .../derivatives/fmriprep/sub-<XX>/ses-1/anat/ | wc -l
   ```
3. **freesurfer dir exists**:
   ```bash
   ls .../derivatives/fmriprep/sourcedata/freesurfer/sub-<XX>/mri/ribbon.mgz
   ```
4. **HTML descriptive text** mentions the right `--bold2anat-init`
   target. If you forced `t1w` but the text says `T2w`, the cache was
   reused.

If any of 1–3 fails, do the 3-path wipe and resubmit.
