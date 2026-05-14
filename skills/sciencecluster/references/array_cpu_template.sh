#!/bin/bash
# CPU array job template — drop in `slurm_jobs/`, copy + edit.
#
# Designed for embarrassingly-parallel per-(subject, chunk) fits where
# each task runs ~10-30 min on CPU. Submit with:
#
#   sbatch --array=1-300%50 --time=00:30:00 \
#          --export=ALL,SUBJECT=2,MODEL=4,N_CHUNKS=40 \
#          array_cpu_template.sh
#
# Tune --array=...%N to throttle concurrent task starts (see the
# sciencecluster skill's ArrayTaskThrottle section).

#SBATCH --job-name=cpu_array
#SBATCH --account=<your-account>
#SBATCH --partition=standard
#SBATCH --output=/dev/null
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G
# NOTE: --time is set at submit time (sbatch --time=...) so the same
# script can be used for short and long jobs. Tight walltime helps
# fair-share priority.

set -eo pipefail          # NO -u: conda activate trips on it.

# Stagger start to avoid NFS dogpile when many tasks dispatch
# simultaneously (env retrieval from $HOME/.bashrc).
sleep $(( RANDOM % 30 ))

# --- Logging: one file per task under ~/logs/ ---
LOGFILE="$HOME/logs/${SLURM_JOB_NAME:-job}_${SLURM_JOB_ID}_${SLURM_ARRAY_TASK_ID:-0}.txt"
mkdir -p "$(dirname "$LOGFILE")"
exec >"$LOGFILE" 2>&1

# --- Required env vars (passed via --export=ALL,VAR=...) ---
if [[ -z "${SUBJECT:-}" || -z "${SLURM_ARRAY_TASK_ID:-}" ]]; then
    echo "ERROR: SUBJECT + SLURM_ARRAY_TASK_ID required." >&2
    exit 2
fi

chunk_idx=$(( SLURM_ARRAY_TASK_ID - 1 ))
sub_pad=$(printf "%02d" "$SUBJECT")

# Rename the job in squeue with informative tag. WARNING: in array
# jobs, the JobName is shared — whichever task renames LAST wins for
# the whole array. So don't put the array index here; it'd mislead.
scontrol update jobid="${SLURM_JOB_ID}" \
    name="myjob_sub-${sub_pad}" 2>/dev/null || true

echo "Host:    $(hostname)"
echo "Task:    sub-${sub_pad} chunk ${chunk_idx}/${N_CHUNKS:-?} array_task=${SLURM_ARRAY_TASK_ID}"
echo "Started: $(date)"

# --- Conda env activation. Replace <path-to-miniforge> + <env>. ---
source "<path-to-miniforge>/etc/profile.d/conda.sh"
conda activate <env>
export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-8}"

# --- Force CPU-only execution if env has CUDA ---
export CUDA_VISIBLE_DEVICES=-1

# --- The work ---
"$HOME/data/conda/envs/<env>/bin/python" -u path/to/script.py \
    "$SUBJECT" \
    --chunk-index "$chunk_idx" \
    --n-chunks "${N_CHUNKS:-1}"

echo "Finished: $(date)"
