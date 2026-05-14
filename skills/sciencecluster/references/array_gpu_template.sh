#!/bin/bash
# GPU array job template — drop in `slurm_jobs/`, copy + edit.
#
# Key differences from the CPU template:
#  - --gres=gpu:1                  request one GPU
#  - --constraint="L4|V100|A100"   tolerate any of these GPU types
#  - 30s random startup stagger    defuses the cuInit race when many
#                                  tasks land on the same 8-GPU node
#                                  simultaneously
#  - Excludes H100/H200 (sm_90 needs CUDA 12; CUDA 11.x envs can't use)
#
# Submit with array throttle to avoid NFS dogpile:
#
#   sbatch --array=1-100%30 --time=00:35:00 \
#          --export=ALL,SUBJECT=2,MODEL=4,N_CHUNKS=10 \
#          array_gpu_template.sh

#SBATCH --job-name=gpu_array
#SBATCH --account=<your-account>
#SBATCH --partition=standard
#SBATCH --output=/dev/null
#SBATCH --gres=gpu:1
#SBATCH --constraint="L4|V100|A100"
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G

set -eo pipefail

# 30s random stagger — defuses cuInit race on multi-GPU nodes AND the
# NFS profile-read dogpile (held-tasks issue). Critical when the array
# is large; harmless when small.
sleep $(( RANDOM % 30 ))

# Logging
LOGFILE="$HOME/logs/${SLURM_JOB_NAME:-job}_${SLURM_JOB_ID}_${SLURM_ARRAY_TASK_ID:-0}.txt"
mkdir -p "$(dirname "$LOGFILE")"
exec >"$LOGFILE" 2>&1

# Required env vars
if [[ -z "${SUBJECT:-}" || -z "${SLURM_ARRAY_TASK_ID:-}" ]]; then
    echo "ERROR: SUBJECT + SLURM_ARRAY_TASK_ID required." >&2
    exit 2
fi

chunk_idx=$(( SLURM_ARRAY_TASK_ID - 1 ))
sub_pad=$(printf "%02d" "$SUBJECT")
scontrol update jobid="${SLURM_JOB_ID}" \
    name="myjob_gpu_sub-${sub_pad}" 2>/dev/null || true

echo "Host:        $(hostname)"
echo "CUDA visible: ${CUDA_VISIBLE_DEVICES:-unset}"
echo "Task:        sub-${sub_pad} chunk ${chunk_idx}/${N_CHUNKS:-?}"
echo "Started:     $(date)"

# CUDA runtime: most TF/JAX wheels bundle their own CUDA; no `module
# load` needed. If your env needs system CUDA, source lmod first:
#   source /etc/profile.d/lmod.sh
# Then point LD_LIBRARY_PATH at the right CUDA tree.

# Conda env activation (CUDA-built env)
source "<path-to-miniforge>/etc/profile.d/conda.sh"
conda activate <cuda-env>
export PYTHONUNBUFFERED=1

# Sanity check the GPU is visible
python -c "import tensorflow as tf; print('GPUs:', tf.config.list_physical_devices('GPU'))" 2>&1 | tail -3
# or for JAX:
# python -c "import jax; print('backend:', jax.default_backend()); print('devs:', jax.devices())"

# --- The work ---
"$HOME/data/conda/envs/<cuda-env>/bin/python" -u path/to/script.py \
    "$SUBJECT" \
    --chunk-index "$chunk_idx" \
    --n-chunks "${N_CHUNKS:-1}"

echo "Finished:    $(date)"
