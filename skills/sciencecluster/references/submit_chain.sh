#!/bin/bash
# Submission orchestrator — chains dependent jobs with afterok.
#
# Pattern: a multi-phase pipeline where each phase's array waits for
# the previous phase to complete successfully:
#
#   phase1 (per-subject chunks) → phase2 (merge) → phase3 (downstream)
#
# Prefer **per-subject** chains over phase-wide afterok across all subjects:
# if one subject's phase1 fails, only that subject's downstream gets stuck,
# not the whole array. Easier to recover (resubmit just that chain) and
# avoids a single noisy voxel blocking 30 subjects' merges.
#
# Adapt the phase scripts (`phase1_chunks.sh` etc.) to your own jobs —
# they should look like `array_cpu_template.sh` / `array_gpu_template.sh`
# with their own python entry points.
#
# Usage:
#   bash submit_chain.sh
#   SUBJECTS="3 5 8" bash submit_chain.sh

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
S_CHUNKS="$SCRIPT_DIR/phase1_chunks.sh"      # CPU/GPU array, N_CHUNKS per subject
S_MERGE="$SCRIPT_DIR/phase2_merge.sh"        # one merge task per subject
S_DOWNSTREAM="$SCRIPT_DIR/phase3_downstream.sh"   # one task per ROI

SUBJECTS="${SUBJECTS:-$(seq 1 30)}"
N_CHUNKS=40
N_ROIS=11

sb() { sbatch "$@" | awk '{print $4}'; }

for sub in $SUBJECTS; do
    sp=$(printf "%02d" "$sub")

    # Phase 1: chunks. Variables go in front of the call (VAR=x sb ...; bash
    # passes them to sbatch inside the function), never as an --export list:
    # that triggers "user env retrieval failed requeued held" (SKILL.md).
    J_CHUNKS=$(SUBJECT=$sub N_CHUNKS=$N_CHUNKS sb --array=1-${N_CHUNKS} --time=00:35:00 \
        "$S_CHUNKS")

    # Phase 2: merge — waits for ALL phase1 tasks for this subject.
    J_MERGE=$(SUBJECT=$sub sb --time=00:05:00 \
        --dependency=afterok:$J_CHUNKS \
        "$S_MERGE")

    # Phase 3: downstream — fan out across ROIs once merge is done.
    J_DOWN=$(SUBJECT=$sub sb --array=1-${N_ROIS} --time=00:25:00 \
        --dependency=afterok:$J_MERGE \
        "$S_DOWNSTREAM")

    echo "sub-${sp}: chunks=$J_CHUNKS merge=$J_MERGE downstream=$J_DOWN"
done

cat <<'EOF'

All chains submitted. Useful follow-ups:

  # Live status grouped by job name
  squeue --me -h --format='%j %T' | sort | uniq -c | sort -rn

  # Cancel zombie pending tasks (DependencyNeverSatisfied)
  squeue --me -h -t PD --format='%i %r' | awk '/DependencyNeverSatisfied/ {print $1}' \
      | awk -F_ '{print $1}' | sort -u | xargs -r scancel

  # Tasks held with "user env retrieval failed": exclude the bad node, release
  # in waves (cause: an --export list; see SKILL.md)
  ~/git/gilles-claude-skills/skills/sciencecluster/scripts/heal_env_holds.sh
EOF
