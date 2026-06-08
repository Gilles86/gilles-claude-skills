#!/bin/bash
# fmriprep wrapper template — lives at <package>/cluster_preproc/fmriprep.sh
# (per the cogneuro-project skill). Replace <project> (BIDS dataset short
# name, e.g. abstractvalue) and <version> (apptainer image tag) before use.
#
# Two ways to run:
#
#   Numeric subjects (array job):
#     sbatch --array=1-30 fmriprep.sh        # -> labels 001, 002, ..., 030
#
#   Any subject by name (single job, overrides the array):
#     sbatch --export=PARTICIPANT_LABEL=pil02 fmriprep.sh
#
# Force a different BOLD2ANAT init (default fmriprep `auto` picks T2w when
# present, which has historically given bad registration with our
# cross-session T2w acquisitions — see SKILL.md "--bold2anat-init"):
#     sbatch --export=ALL,BOLD2ANAT_INIT=t1w --array=1-30 fmriprep.sh
#
#SBATCH --job-name=fmriprep_<project>
#SBATCH --output=/home/gdehol/logs/<project>_fmriprep_%A-%a.txt
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=64G
#SBATCH --time=24:00:00
# 3+ session subjects: bump to --partition=standard --qos=medium (48h cap)
# and --mem=96G.

if [ -z "$PARTICIPANT_LABEL" ]; then
    PARTICIPANT_LABEL=$(printf "%03d" $SLURM_ARRAY_TASK_ID)
fi

EXTRA_ARGS=""
if [ -n "$BOLD2ANAT_INIT" ]; then
    EXTRA_ARGS="--bold2anat-init $BOLD2ANAT_INIT"
fi

# `source /etc/profile.d/lmod.sh` alone defines `module` but leaves
# MODULEPATH empty — module load works for interactive sbatch (which
# inherits MODULEPATH from the submitting login shell), but fails when the
# job is submitted from a cleaner env (e.g. snakemake-executor-plugin-slurm).
# `source /etc/profile` sources the whole chain incl. MODULEPATH.
# See: sciencecluster skill, "module in SLURM scripts".
source /etc/profile
module load apptainer/1.4.1

export APPTAINERENV_FS_LICENSE=$HOME/freesurfer/license.txt

FILTER_FILE=$(mktemp /tmp/bids_filter_XXXXXX.json)
cat > "$FILTER_FILE" << 'EOF'
{
    "fmap": {"datatype": "fmap"},
    "bold": {"datatype": "func", "suffix": "bold"},
    "t1w":  {"datatype": "anat", "suffix": "T1w"},
    "t2w":  {"datatype": "anat", "suffix": "T2w"}
}
EOF

apptainer run \
  -B /shares/zne.uzh/containers/templateflow:/opt/templateflow \
  -B /shares/zne.uzh/gdehol/ds-<project>:/data \
  -B /scratch/gdehol:/workflow \
  -B ${FILTER_FILE}:/bids_filter.json \
  --cleanenv /shares/zne.uzh/containers/fmriprep-<version> \
    /data /data/derivatives/fmriprep participant \
  --participant-label $PARTICIPANT_LABEL \
  --bids-filter-file /bids_filter.json \
  --output-spaces T1w fsnative \
  --skip_bids_validation \
  -w /workflow \
  --nthreads 16 \
  --omp-nthreads 16 \
  --low-mem \
  --no-submm-recon \
  $EXTRA_ARGS
APPTAINER_RC=$?

# Treat the apptainer exit code as the primary signal, but tolerate
# spurious exit-1 from apptainer >= 1.4 on otherwise-clean runs. The naive
# "if exit-nonzero and html exists, treat as clean" version got bitten by
# fmriprep writing a *failure-report* HTML on real failures (sub-12 /
# 3573299 on 2026-05-29: ZRAN_READ_FAIL, `fMRIPrep failed: 15 raised`,
# apptainer exit 1, *html written anyway*). The discriminator below adds a
# late-stage output check written only after freesurfer autorecon completes
# — present on truly-finished runs, absent on early failures like ZRAN.
# For pilots with no ses-1 anat acquisition, pick a different late output.
APARCASEG="/shares/zne.uzh/gdehol/ds-<project>/derivatives/fmriprep/sub-${PARTICIPANT_LABEL}/ses-1/anat/sub-${PARTICIPANT_LABEL}_ses-1_desc-aparcaseg_dseg.nii.gz"
if [[ $APPTAINER_RC -ne 0 ]]; then
    if [[ -f "$APARCASEG" ]]; then
        echo "apptainer exited $APPTAINER_RC but late-stage anat output exists ($APARCASEG) — treating as spurious exit, clean run."
    else
        echo "apptainer exited $APPTAINER_RC and late-stage anat output missing ($APARCASEG) — fmriprep failed."
        exit $APPTAINER_RC
    fi
fi

# Completion sentinel — touched ONLY after the discriminator above passes,
# so its existence is a hard guarantee fmriprep ran to its end. Use this as
# the Snakemake rule output (`.fmriprep_done`), NOT the HTML. See SKILL.md
# "The html exists != fmriprep succeeded".
DONE="/shares/zne.uzh/gdehol/ds-<project>/derivatives/fmriprep/sub-${PARTICIPANT_LABEL}/.fmriprep_done"
mkdir -p "$(dirname "$DONE")"
touch "$DONE"
echo "fmriprep done sentinel: $DONE"
