#!/usr/bin/env bash
# ============================================================================
# REAL EXEMPLAR — excerpted from a working project.
#
# Provenance: ~/git/abstract_values/ingest_new_session.sh @ b91dff1
#
# What to study (the pre-cluster orchestration pattern):
#   * Top docstring is an ENUMERATED PIPELINE — every step the script will
#     run is listed with its number. Update the docstring when steps shift.
#   * `usage()` extracts itself from the header (`sed -n '2,/^set -/p'`).
#     No drift between code and --help text.
#   * Long-form flags (--subject, --session, --source-dir, --dry-run) via
#     a while/case loop. Required args (`--subject`, `--session`) are
#     checked at the end.
#   * Defaults live at the top in named CONSTANTS (BIDS_ROOT, NETWORK_BASE,
#     CLUSTER, CLUSTER_BIDS, GLMSINGLE_DERIV). Easy to spot and override.
#   * **Completeness gate** before any writes: counts ses-* directories
#     on the network drive against EXPECTED_MRI_SESSIONS (2 for study,
#     1 for pilots). FORCE_INCOMPLETE=1 overrides for debug runs.
#     Refuses to start MRI ingest for an incomplete subject — fail loud
#     and early rather than half-ingest and confuse downstream.
#   * Step 1 (rsync source → local) has a fallback: if the network drive
#     is unmounted but local sourcedata already exists, skip the rsync
#     rather than erroring. Lets you re-run on already-pulled data.
#   * Step 2b is a sanity gate on the BOLD run count after conversion —
#     warns if the run count is off and asks interactively before proceeding.
#   * `log()` is just a timestamp + echo. Use it for every step boundary so
#     long ingest runs have an audit trail in stdout.
#
# EXCERPT NOTE: the file continues past line ~200 with a long heredoc that
# submits the full SLURM chain (fmriprep → glmsingle → fit_aprf/cv/sessionshift,
# fit_vonmises/cv, decode_gabor/value per ROI, compute_fisher_information × 2).
# That part is project-specific — see the provenance file for the full source.
# ============================================================================
# ingest_new_session.sh — end-to-end pipeline for a new MRI session.
#
# Local steps:
#   1. rsync source data  →  local BIDS sourcedata
#   2. BIDS conversion (dry-run preview, then real)
#   3. rsync BIDS session + behavior  →  cluster
#
# Cluster SLURM chain (all chained with --dependency=afterok):
#   4. fmriprep              (full subject, all sessions)
#   5. GLMsingle             (all sessions jointly, after fmriprep)
#
#   After GLMsingle (all parallel):
#   6.  fit_aprf             (standard)
#   7.  fit_aprf_cv
#   8.  fit_aprf session-shift   (only ses≥2)
#   9.  fit_aprf_cv session-shift (only ses≥2)
#  10.  fit_aprf_weighted
#  11.  fit_aprf_weighted_cv
#  12.  fit_vonmises
#  13.  fit_vonmises_cv
#  14.  decode_gabor         (per ROI in DECODE_ROIS)
#  15.  decode_value         (per ROI in DECODE_ROIS)
#  16.  compute_fisher_information  (Von Mises FI, per ROI in FI_ROIS_VONMISES)
#
#   After fit_aprf:
#  17.  compute_fisher_information_aprf  (per ROI in FI_ROIS_APRF)
#
# Prerequisites:
#   ROI masks must exist under derivatives/masks/sub-<subject>/ses-1/anat/
#   before the pipeline is submitted (run get_surface_roi_mask.py after fmriprep).
#
# Usage:
#   ./ingest_new_session.sh --subject pil02 --session 2
#   ./ingest_new_session.sh --subject pil02 --session 2 \
#       --source-dir /custom/path/ses-2
#   ./ingest_new_session.sh --subject pil02 --session 2 --dry-run
#
# Options:
#   --subject LABEL       participant label, e.g. pil02 or 01 (required)
#   --session N           session number (required)
#   --source-dir PATH     source ses-N directory (default: network drive)
#   --glmsingle-deriv L   fmriprep derivative for GLMsingle (default: fmriprep)
#   --dry-run             show BIDS conversion preview; skip all writes and cluster jobs

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── defaults ──────────────────────────────────────────────────────────────────
BIDS_ROOT="/data/ds-abstractvalue"
NETWORK_BASE='/Volumes/g_econ_department$/projects/2026/dehollander_bedi_ruff_abstract_values/data/sourcedata/mri'
CLUSTER="sciencecluster"
CLUSTER_BIDS="/shares/zne.uzh/gdehol/ds-abstractvalue"
GLMSINGLE_DERIV="fmriprep"
DRY_RUN=0

# ROIs for decode and FI jobs — format: "DESC:HEMI" (HEMI=None omits hemi entity)
DECODE_ROIS="BensonV1:LR NPCr:None"
DECODE_N_VOXELS="0 50 100 250 500"
DECODE_LAMBDAS="0.0 0.1"
FI_ROIS_VONMISES="BensonV1:LR"
FI_ROIS_APRF="NPCr:None"

# ── argument parsing ──────────────────────────────────────────────────────────
SUBJECT=""
SESSION=""
SOURCE_DIR=""

usage() {
    sed -n '2,/^set -/p' "$0" | grep '^#' | sed 's/^# \{0,1\}//'
    exit 1
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --subject)         SUBJECT="$2";        shift 2 ;;
        --session)         SESSION="$2";        shift 2 ;;
        --source-dir)      SOURCE_DIR="$2";     shift 2 ;;
        --glmsingle-deriv) GLMSINGLE_DERIV="$2"; shift 2 ;;
        --dry-run)         DRY_RUN=1;           shift   ;;
        -h|--help)         usage ;;
        *) echo "Unknown option: $1" >&2; usage ;;
    esac
done

[[ -z "$SUBJECT" || -z "$SESSION" ]] && { echo "Error: --subject and --session are required." >&2; usage; }

SOURCE_DIR="${SOURCE_DIR:-${NETWORK_BASE}/sub-${SUBJECT}/ses-${SESSION}}"
BIDS_SOURCEDATA="${BIDS_ROOT}/sourcedata/mri/sub-${SUBJECT}"

log() { echo "[$(date '+%H:%M:%S')] $*"; }

# ── completeness gate ────────────────────────────────────────────────────────
# Policy: never start MRI ingestion for subjects that don't yet have all
# expected MRI sessions on the network drive. Override with FORCE_INCOMPLETE=1.
#   Default: 2 sessions for study subjects (sub-NN); 1 session for pilots (sub-pilNN).
EXPECTED_MRI_SESSIONS="${EXPECTED_MRI_SESSIONS:-2}"
if [[ "$SUBJECT" == pil* ]]; then
    EXPECTED_MRI_SESSIONS="${EXPECTED_MRI_SESSIONS_PILOT:-1}"
fi

if [[ "$DRY_RUN" -eq 0 && "${FORCE_INCOMPLETE:-0}" -ne 1 ]]; then
    network_mri="${NETWORK_BASE}/sub-${SUBJECT}"
    if [[ -d "$network_mri" ]]; then
        actual=$(find "$network_mri" -maxdepth 1 -mindepth 1 -type d -name 'ses-*' | wc -l | tr -d ' ')
    else
        actual=0
    fi
    if (( actual < EXPECTED_MRI_SESSIONS )); then
        cat >&2 <<EOF
Error: sub-${SUBJECT} has ${actual} of ${EXPECTED_MRI_SESSIONS} expected MRI sessions on the
network drive (${network_mri}). Refusing to start MRI ingest for an incomplete subject.

Options:
  • Wait until the missing session(s) appear, then re-run.
  • For behavior-only ingest, use the /ingest skill with --scope behavior-cluster
    (this script is MRI-side only).
  • To override (e.g. debug runs), set FORCE_INCOMPLETE=1.
EOF
        exit 2
    fi
fi


# ── step 1: rsync source → local BIDS sourcedata ─────────────────────────────
# If the SMB share is unmounted but local sourcedata already has this session,
# skip the rsync rather than aborting — useful for "re-submit existing data"
# runs where the network drive isn't currently mounted.
if [[ ! -d "$SOURCE_DIR" ]]; then
    if [[ -d "${BIDS_SOURCEDATA}/ses-${SESSION}" ]]; then
        log "Step 1: ${SOURCE_DIR} not available (unmounted?); local sourcedata exists — skipping rsync."
    else
        echo "Error: source ${SOURCE_DIR} not available AND local sourcedata ${BIDS_SOURCEDATA}/ses-${SESSION} is missing. Mount the network drive first." >&2
        exit 1
    fi
else
    log "Step 1: rsync ${SOURCE_DIR}  →  ${BIDS_SOURCEDATA}/"
    if [[ "$DRY_RUN" -eq 1 ]]; then
        rsync -av --dry-run "${SOURCE_DIR}" "${BIDS_SOURCEDATA}/"
    else
        rsync -av "${SOURCE_DIR}" "${BIDS_SOURCEDATA}/"
    fi
fi

# ── step 2: BIDS conversion ───────────────────────────────────────────────────
log "Step 2: BIDS conversion — dry-run preview"
conda run -n abstract_values python "${SCRIPT_DIR}/fix_and_move_bids.py" \
    --subject "${SUBJECT}" --session "${SESSION}" --dry-run

if [[ "$DRY_RUN" -eq 1 ]]; then
    log "Dry-run mode — stopping before any writes."
    exit 0
fi

log "Step 2: BIDS conversion — writing"
conda run -n abstract_values python "${SCRIPT_DIR}/fix_and_move_bids.py" \
    --subject "${SUBJECT}" --session "${SESSION}"

# ── step 2b: verify expected BOLD run count ─────────────────────────────────
EXPECTED_BOLD=8
BIDS_FUNC="${BIDS_ROOT}/sub-${SUBJECT}/ses-${SESSION}/func"
ACTUAL_BOLD=$(find "${BIDS_FUNC}" -name "sub-*_task-*_run-*_bold.nii.gz" 2>/dev/null | wc -l | tr -d ' ')
if [[ "${ACTUAL_BOLD}" -ne "${EXPECTED_BOLD}" ]]; then
    log "WARNING: expected ${EXPECTED_BOLD} BOLD runs in ${BIDS_FUNC}, found ${ACTUAL_BOLD}"
    log "Check for aborted/partial runs. Listing BOLD files by size:"
    ls -lhS "${BIDS_FUNC}"/sub-*_task-*_run-*_bold.nii.gz 2>/dev/null
    read -rp "Continue anyway? [y/N] " answer
    [[ "${answer}" =~ ^[Yy]$ ]] || { log "Aborting."; exit 1; }
fi

# ── step 3a: rsync ENTIRE subject BIDS tree → cluster ────────────────────────
# Push the whole sub-X/ tree (all sessions present locally) rather than just
# ses-N. rsync is idempotent — existing files on the cluster are no-ops, so
# the cost of including older sessions is a brief stat scan. This covers the
# first-time multi-session case where sub-X has multiple BIDS-converted
# sessions locally but the cluster has none (or some of) them yet.
log "Step 3a: rsync ${BIDS_ROOT}/sub-${SUBJECT}/  →  cluster (all sessions)"
ssh "${CLUSTER}" "mkdir -p ${CLUSTER_BIDS}/sub-${SUBJECT}"
rsync -av \
    "${BIDS_ROOT}/sub-${SUBJECT}/" \
    "${CLUSTER}:${CLUSTER_BIDS}/sub-${SUBJECT}/"

# ── step 3b: rsync ENTIRE subject behavior tree → cluster ────────────────────
BEHAVIOR_SRC="${BIDS_ROOT}/sourcedata/behavior/sub-${SUBJECT}"
BEHAVIOR_DST="${CLUSTER}:${CLUSTER_BIDS}/sourcedata/behavior/sub-${SUBJECT}/"
if [[ -d "${BEHAVIOR_SRC}" ]]; then
    log "Step 3b: rsync behavior sourcedata  →  cluster (all sessions)"
    ssh "${CLUSTER}" "mkdir -p ${CLUSTER_BIDS}/sourcedata/behavior/sub-${SUBJECT}"
    rsync -av "${BEHAVIOR_SRC}/" "${BEHAVIOR_DST}"
else
    log "Step 3b: no behavior sourcedata found at ${BEHAVIOR_SRC}, skipping"
fi

# ── steps 4–17: SLURM chain on cluster ───────────────────────────────────────
# See the provenance file for the full heredoc that submits the dependency-chained
# pipeline (fmriprep → glmsingle → encoding-model fits per ROI → decoding →
# Fisher information). The pattern is: capture each parsable JobID into a shell
# variable, then `sbatch --dependency=afterok:$PARENT_JID ...` for the child.
