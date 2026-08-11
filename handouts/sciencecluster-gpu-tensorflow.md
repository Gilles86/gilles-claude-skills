# GPU jobs on UZH sciencecluster: why TensorFlow/braincoder silently falls back to CPU, and how to fix it

Drop this file into your project's Claude context (e.g. next to `CLAUDE.md`,
or as a skill reference) if your SLURM jobs land on GPU nodes but run on the
CPU anyway — the classic symptom is a braincoder/TensorFlow decoding or
PRF-fitting job taking ~25× longer than expected and eventually hitting
walltime.

Fill in these placeholders for your own setup:

- `<account>` — your SLURM account (`sacctmgr show user $USER withassoc format=account`)
- `<conda-base>` — your conda install root (e.g. `$HOME/data/miniforge3`)
- `<conda-envs>` — your envs dir (e.g. `$HOME/data/conda/envs`)
- `<cuda-env>` — the CUDA-built conda env for the job

The full operational skill (partitions, QoS, exit codes, array throttling,
apptainer, etc.) lives at
<https://github.com/Gilles86/gilles-claude-skills> — this handout is the
GPU-specific extract.

## TL;DR checklist when "the GPU node isn't using the GPU"

Work through these in order; each one produces the *identical* symptom
(TensorFlow silently computes on CPU):

1. **No `--gres=gpu:1` in the job.** There is **no GPU partition** on
   sciencecluster — being scheduled onto a node that happens to have GPUs
   gives you zero GPU access. Without `--gres`, SLURM's cgroup hides all
   GPUs and TF sees an empty device list. The *only* way to get a GPU is
   `#SBATCH --gres=gpu:1`.
2. **The conda env is not CUDA-built.** Plain `pip install tensorflow` (or a
   CPU env reused "temporarily") falls back to CPU without any error. You
   need `tensorflow[and-cuda]` (or `jax[cuda12]` / `torch+cu*`) — these
   wheels bundle their own CUDA runtime, so no `module load cuda` is needed
   at all.
3. **cuInit race on multi-GPU nodes** (the sneaky one — see below). Several
   array tasks landing on the same 8-GPU V100/A100/H100 box at the same
   moment issue parallel `cuInit` calls that deadlock the NVIDIA driver.
   Each job *has* a GPU allocated, but TF's device probe fails and it
   silently falls back to CPU.
4. **CUDA 11 env scheduled onto an H100/H200.** sm_90 needs CUDA 12; a CUDA
   11.x env can't initialize those GPUs. Exclude them with
   `--constraint="L4|V100|A100"` until the env is on CUDA 12.

## Fail fast: never let a GPU job quietly run on CPU

Add this to the top of every GPU job script, right after env activation.
A job that dies in 20 seconds with a clear error beats one that burns 6
hours of walltime on CPU:

```bash
python - <<'EOF'
import sys, tensorflow as tf
gpus = tf.config.list_physical_devices('GPU')
print('GPUs visible:', gpus, flush=True)
if not gpus:
    sys.exit('FATAL: no GPU visible to TensorFlow — aborting instead of CPU fallback')
EOF
```

(JAX equivalent: `import jax; assert jax.default_backend() == 'gpu'`.)

Combined with `set -eo pipefail`, the job FAILs immediately and you can
diagnose from the log instead of discovering the problem via `sacct`
Elapsed times a day later.

## The cuInit race, and the fix that actually works

**Symptom:** an array of GPU jobs where *some* tasks run fast (GPU) and
others run ~25× slower (CPU fallback), correlated with several tasks
starting on the same node within the same few seconds. TF logs may show
CUDA init errors, or nothing at all.

**Why random stagger is not enough:** with 8 jobs racing in a 30 s window,
the chance that all start ≥1 s apart (the driver-init window) is ~10%.
Empirically ~90% of such bursts deadlock at least one task.

**Fix: per-node `flock` warm-up.** The first job on each node performs a
minimal CUDA init under an exclusive node-local lock; everyone else waits a
few seconds and then finds a warm driver:

```bash
LOCK="/tmp/cuinit_warm_$(hostname -s).flock"
(
    flock -w 60 -x 200 || { echo "WARN: cuInit lock timeout"; exit 0; }
    python -c "
import os
os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '3')
import tensorflow as tf
print(f'cuInit OK: {len(tf.config.list_physical_devices(\"GPU\"))} GPU(s)', flush=True)
"
) 200>"$LOCK"
```

Why this shape: `/tmp` is node-local (an NFS lock would serialize across
*all* nodes, which is wrong); the kernel releases `flock` when the holder
dies (crash-safe); `-w 60` bounds the wait. Keep a *separate* short random
stagger (`sleep $((RANDOM % 15))`) for the NFS dogpile at array start —
that's a different race. `ArrayTaskThrottle` does not prevent cuInit races
either: 8 of 50 concurrent tasks can still land on one node.

The L4 nodes have 1 GPU per node, so they can't race — the problem lives on
the 8-GPU V100/A100/H100 boxes.

## Reference GPU job script

```bash
#!/bin/bash
#SBATCH --job-name=decode_gpu
#SBATCH --account=<account>
#SBATCH --partition=lowprio          # GPU-bound work: lowprio dispatches fast
#SBATCH --gres=gpu:1
#SBATCH --constraint="L4|V100|A100"  # drop H100/H200 unless env is CUDA 12
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=01:00:00              # tight walltime = better priority
#SBATCH --output=/home/%u/logs/%x_%A_%a.txt

set -eo pipefail                      # NOT set -u (conda activation breaks under -u)
export PYTHONUNBUFFERED=1

sleep $(( RANDOM % 15 ))              # NFS-dogpile stagger (separate from cuInit fix)

echo "Host: $(hostname)  CUDA_VISIBLE_DEVICES: ${CUDA_VISIBLE_DEVICES:-unset}"

source "<conda-base>/etc/profile.d/conda.sh"
conda activate <cuda-env>
export KERAS_BACKEND=tensorflow       # braincoder (Keras 3): pin the backend explicitly

# --- cuInit warm-up (multi-GPU nodes) ---
LOCK="/tmp/cuinit_warm_$(hostname -s).flock"
(
    flock -w 60 -x 200 || { echo "WARN: cuInit lock timeout"; exit 0; }
    python -c "import os; os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL','3'); import tensorflow as tf; print('cuInit OK:', len(tf.config.list_physical_devices('GPU')), 'GPU(s)', flush=True)"
) 200>"$LOCK"

# --- fail fast if the GPU still isn't visible ---
python - <<'EOF'
import sys, tensorflow as tf
gpus = tf.config.list_physical_devices('GPU')
print('GPUs visible:', gpus, flush=True)
if not gpus:
    sys.exit('FATAL: no GPU visible — aborting instead of silent CPU fallback')
EOF

# --- the actual work ---
exec python -u path/to/decode_script.py "$SUBJECT" --bids-folder /shares/<account>/...
```

Notes baked into that template:

- **`exec python -u`** (not `conda run`): `conda run` buffers *all* stdout
  until exit — the log freezes at the first lines for the whole run, so you
  can't tell a working job from a hung one — and it doesn't forward SIGTERM
  on `scancel`/timeout. If you must keep `conda run`, it has to be
  `conda run --no-capture-output -n <env> python -u …`, and it still won't
  forward signals.
- **`KERAS_BACKEND=tensorflow`**: braincoder on Keras 3 respects this env
  var; pin it so the job never picks up a stray backend setting.
- **No `module load cuda`**: `tensorflow[and-cuda]` / `jax[cuda12]` wheels
  bundle their own CUDA runtime. `module load` is only for envs that
  explicitly link the system CUDA stack (rare).

## Building the CUDA env (no GPU node needed)

You do **not** need `--gres=gpu:1` to *build* the env — the modern wheels
are precompiled and ship their CUDA runtime; the install is pure wheel
extraction, and CUDA initializes lazily at first device use inside the
running job. (Verified end-to-end on sciencecluster 2026-05-27: env built
on a CPU node, TF/JAX/torch all detected an L4 in a later `--gres` job.)

Do submit the build as an sbatch job though — `conda create` + `pip
install` forks enough processes to blow the login node's ulimit (256):

```bash
#SBATCH --partition=lowprio
#SBATCH --cpus-per-task=4 --mem=16G --time=30:00
source "<conda-base>/etc/profile.d/conda.sh"
conda env create -p <conda-envs>/<cuda-env> -f environment_cuda.yml
```

## Diagnosing after the fact: did the job actually use the GPU?

- **Log line**: with the fail-fast guard above, `grep 'GPUs visible' log`
  answers it directly. Without it, TF prints
  `Created device /device:GPU:0` when it got the GPU, nothing when it
  didn't.
- **Runtime**: `sacct -j <jobid> --format=JobID,JobName%25,Elapsed,State` —
  a CPU-fallback task runs ~25× longer than its GPU siblings in the same
  array.
- **Live check on a running job**: `srun --jobid=<jobid> --overlap nvidia-smi`
  — the python process should be listed with GPU memory; if `nvidia-smi`
  shows 0 MiB used while the job computes, it's on CPU.
- **Frozen-looking log but job "running"**: probably the `conda run`
  buffering trap, not a hang — `sstat -j <jobid> --format=AveCPU` showing
  CPU time accruing is the tell.

## One more trap: porting a GPU script to CPU

If GPU queues are congested and you rerun the same script on CPU, the
memory budget does *not* transfer: GPU cuBLAS/cuDNN fuse matmul
intermediates in on-chip scratch, while CPU TF materializes them in RAM. A
voxel-chunk size that fits in a 16 GB GPU can OOM-kill a 16 GB CPU job in
minutes. Shrink the inner chunk 5–10× before porting, or stay on GPU.
