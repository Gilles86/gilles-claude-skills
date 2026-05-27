# GPU jobs

**When to load:** writing or debugging any `--gres=gpu:1` job. Also
when GPU queues are congested and you're considering switching to
CPU on the same script — the memory budget doesn't transfer linearly.

## Basics

No special partition required. Request a GPU with `--gres=gpu:1`.
Conda envs that bundle their own CUDA runtime (`jax[cuda12]`,
`tensorflow[and-cuda]` wheels) work without any `module load` at
all, since SLURM sets `CUDA_VISIBLE_DEVICES` from the `--gres`
allocation and the bundled CUDA libs handle the rest. Reserve
`module load cuda/...` for envs that explicitly need the system
CUDA stack (rare). If a custom env DOESN'T bundle CUDA, follow the
`script_shell_setup.md` rules for `#!/bin/bash -l`.

```bash
#SBATCH --gres=gpu:1
# No `module load` needed — jax[cuda12] / tensorflow-gpu bundle their own CUDA.
source "<conda-base>/etc/profile.d/conda.sh"
conda activate <cuda-env>
nvidia-smi               # sanity check
```

GPU fitting only works with a CUDA-built conda env. A standard CPU
env silently falls back to CPU. **Build the CUDA env on a GPU compute
node, not the login node** — the install verifies driver compatibility
at install time.

Verify GPU is visible inside a job before long fits:

```bash
python -c "import jax; print('backend:', jax.default_backend()); print('devs:', jax.devices())"
# or for TF:
python -c "import tensorflow as tf; print(tf.config.list_physical_devices('GPU'))"
```

## GPU constraint syntax

`#SBATCH --constraint="L4|V100|A100"` accepts any of those GPU types.
Useful when L4 alone gives long queue waits. **Exclude H100/H200 if
the env is on CUDA 11.x** (sm_90 needs CUDA 12).

## Porting GPU → CPU: memory budget doesn't transfer

When GPU queues are congested and you're tempted to switch to CPU
on the same script, **don't assume the per-task memory budget is
unchanged**. GPU TF / cuBLAS / cuDNN use tile fusion that keeps
matmul intermediates inside on-chip scratch — large `(M, K) @ (K, N)`
operations never materialize the full `(M, K, N)` tensor in DRAM.
CPU TF + OpenBLAS materializes more intermediates and is much more
sensitive to inner-batch size.

Concrete symptom: a parameter-fitting script with
`--voxel-chunk-size 100000` runs fine on a 16 GB GPU but
`OUT_OF_MEMORY`-kills at 16 GB CPU mem within 2 minutes. The fix is
to shrink the inner batch (typically 5–10×) — not to bump `--mem`
indefinitely.

Rule of thumb: when moving a TF fitting workload GPU → CPU, halve
the inner-chunk size and re-measure peak RSS on one task before
launching the array. Easier still: stay on GPU and use a sibling
partition via `partition_swap.md` if the standard GPU queue is the
bottleneck — same hardware, faster dispatch.

## cuInit race on multi-GPU nodes

Multiple jobs landing simultaneously on the same multi-GPU node
(8-GPU V100 / A100 / H100 boxes) issue parallel `cuInit` calls that
deadlock the NVIDIA driver. TF silently falls back to CPU → ~25×
slowdown → walltime timeouts → cascading `DependencyNeverSatisfied`.

Random stagger doesn't reliably fix this — with 8 jobs racing in a
30 s window, the probability that all start ≥ 1 s apart (the driver
init window) is ~10%. Empirically ~90% deadlock.

**Fix: per-node `flock` warm-up.** First job per node does a
minimal CUDA init under an exclusive lock; subsequent jobs see a
warm driver.

```bash
LOCK="/tmp/cuinit_warm_$(hostname -s).flock"
(
    flock -w 60 -x 200 || { echo "WARN: lock timeout"; exit 0; }
    "$PYTHON" -c "
import os
os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '3')
import tensorflow as tf
print(f'cuInit OK: {len(tf.config.list_physical_devices(\"GPU\"))} GPU(s)', flush=True)
"
) 200>"$LOCK"
```

Properties: `/tmp` is node-local (NFS locks would be wrong); kernel
releases `flock` on holder death (crash-safe); `-w 60` timeout
prevents indefinite hangs.

Keep a short random stagger (`sleep $((RANDOM % 15))`) separately
for the **NFS dogpile** at task start — different race, unrelated
to cuInit. `ArrayTaskThrottle` (see `array_throttling.md`) mitigates
NFS dogpile but doesn't prevent cuInit races — 8 of 50 concurrent
tasks can still land on the same node.
