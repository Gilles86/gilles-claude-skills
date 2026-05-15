#!/bin/bash
# Orchestrator: rsync sourcedata → BIDS conversion → upload to cluster →
# submit dependency-chained SLURM pipeline.
#
# Pattern from abstract_values/ingest_new_session.sh — adapt per project.
# Run locally; it ssh's to the cluster for the submission step.
#
# Usage:
#   ./scripts/ingest_new_session.sh <subject> <session> [--dry-run]
#
# Example:
#   ./scripts/ingest_new_session.sh 12 2

set -euo pipefail

SUBJECT="${1:?Usage: $0 <subject> <session> [--dry-run]}"
SESSION="${2:?Usage: $0 <subject> <session> [--dry-run]}"
DRY_RUN=""
[[ "${3:-}" == "--dry-run" ]] && DRY_RUN="--dry-run"

PROJECT="<project>"
LOCAL_BIDS="/data/ds-${PROJECT}"
CLUSTER_BIDS="/shares/zne.uzh/gdehol/ds-${PROJECT}"
CLUSTER_HOST="sciencecluster"
CLUSTER_REPO="~/git/${PROJECT}"

SUBJ_PADDED=$(printf "%02d" "${SUBJECT}")

echo "=== Ingesting sub-${SUBJ_PADDED} ses-${SESSION} ==="

# 1. Rsync sourcedata from scanner workstation (or wherever)
echo "--- 1/5: rsync sourcedata"
rsync -av $DRY_RUN \
    "scanner-host:/raw/sub-${SUBJ_PADDED}/ses-${SESSION}/" \
    "${LOCAL_BIDS}/sourcedata/sub-${SUBJ_PADDED}/ses-${SESSION}/"

# 2. BIDS conversion (local)
echo "--- 2/5: BIDS conversion"
python "<package>/prepare/convert_raw_mri_data.py" \
    --subject "${SUBJ_PADDED}" --session "${SESSION}" \
    --bids_folder "${LOCAL_BIDS}" $DRY_RUN

# 3. Verify behavior files present
echo "--- 3/5: verify behavior"
test -d "${LOCAL_BIDS}/sub-${SUBJ_PADDED}/ses-${SESSION}/func" || {
    echo "ERROR: BIDS func dir missing"; exit 1;
}

# 4. Upload to cluster
echo "--- 4/5: rsync to cluster"
rsync -av $DRY_RUN \
    "${LOCAL_BIDS}/sub-${SUBJ_PADDED}/" \
    "${CLUSTER_HOST}:${CLUSTER_BIDS}/sub-${SUBJ_PADDED}/"

# 5. Submit cluster pipeline (dependency-chained, per-subject)
echo "--- 5/5: submit cluster pipeline"
ssh "${CLUSTER_HOST}" bash <<EOF
set -euo pipefail
cd ${CLUSTER_REPO}
git pull --ff-only

# fmriprep -> glmsingle -> encoding -> decoding, all chained on this subject
JID_FP=\$(sbatch --parsable \\
    --export=PARTICIPANT_LABEL=${SUBJ_PADDED},SESSION=${SESSION} \\
    <package>/cluster_preproc/slurm_jobs/fmriprep.sh)
echo "fmriprep job: \$JID_FP"

JID_GLM=\$(sbatch --parsable --dependency=afterok:\$JID_FP \\
    --export=PARTICIPANT_LABEL=${SUBJ_PADDED},SESSION=${SESSION} \\
    <package>/glm/slurm_jobs/fit_single_trials.sh)
echo "glmsingle job: \$JID_GLM"

JID_PRF=\$(sbatch --parsable --dependency=afterok:\$JID_GLM \\
    --export=PARTICIPANT_LABEL=${SUBJ_PADDED} \\
    <package>/modeling/slurm_jobs/fit_prf.sh)
echo "encoding job: \$JID_PRF"

JID_DEC=\$(sbatch --parsable --dependency=afterok:\$JID_PRF \\
    --export=PARTICIPANT_LABEL=${SUBJ_PADDED} \\
    <package>/modeling/slurm_jobs/decode.sh)
echo "decode job: \$JID_DEC"

echo "Chain submitted: \$JID_FP -> \$JID_GLM -> \$JID_PRF -> \$JID_DEC"
EOF

echo "=== Ingest complete ==="
