# Conda envs on sciencecluster

**When to load:** about to build a new conda env on the cluster, or
deciding where to put it, or debugging an env that won't import its
CUDA libs correctly.

## Where envs live

| Thing | Path |
|---|---|
| Conda base | `~/data/miniforge3` |
| Envs dir | `~/data/conda/envs/<env>` |
| Direct python binary | `~/data/conda/envs/<env>/bin/python` |

Put project envs under `~/data/conda/envs/`, **not** `~/.conda/envs/`
(that dir only holds conda config). The `data/` prefix puts envs on
the high-throughput flash filesystem; building elsewhere is slower
and uses your home quota.

## Building envs: sbatch the build, no GPU needed

**Never build on the login node** — `conda create` + `pip install`
forks lots of processes, easily blows past the login-node ulimit
(256), and hogs memory that other users want for `ls` and `squeue`.
Submit the build as an sbatch job.

**You do NOT need `--gres=gpu:1` for the build**, even for full CUDA
stacks. Verified end-to-end on sciencecluster 2026-05-27 with
`tensorflow[and-cuda]==2.20.*`, `jax[cuda12]`, and `torch+cu130`:

1. Built the env on a `standard` CPU compute node (no `nvidia-smi`,
   no GPU visible at install time). 11 minutes total, mostly
   network-bound (~5 GB of wheels).
2. Activated it on a `--gres=gpu:1` job (NVIDIA L4).
3. TF, JAX, and torch all detected the GPU at runtime and ran a
   matmul on it without any post-install fixup.

Mechanism: modern pip wheels (`nvidia-cuda-runtime-cu*`,
`nvidia-cudnn-cu*`, `tensorflow[and-cuda]`, `jax[cuda12]`,
`torch+cu*`) are precompiled and ship their own CUDA runtime. The
install step is just wheel extraction — no compilation, no driver
probe, no GPU needed. CUDA initializes lazily at first device-use
inside the running job.

A reasonable build job:

```bash
#!/bin/bash
#SBATCH --job-name=build_<env>
#SBATCH --account=<account>
#SBATCH --partition=lowprio
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=30:00
#SBATCH --output=/home/<user>/logs/build_<env>_%j.txt

set -eo pipefail
source "$HOME/data/miniforge3/etc/profile.d/conda.sh"
conda env create -p "$HOME/data/conda/envs/<env>" -f environment.yml
```

`lowprio` is fine — env builds are short and idempotent; even if
preempted, re-invoking resumes from `conda`'s download cache.

## When you DO need a GPU at build time

Rare in 2026. Two real cases:

- **Source builds** — `pip install --no-binary :all: <pkg>`, or
  building custom CUDA kernels (cupy from source, custom PyTorch
  extensions, mojo). Compilation links against the installed CUDA
  toolkit, which is found via runtime probe.
- **Legacy installers** that probed the driver at install time. Most
  popular packages have migrated to wheel-based bundled CUDA;
  unlikely to hit unless using a niche / older library.

If you genuinely need it, add `--gres=gpu:1` to the build sbatch.

## Activating inside a SLURM job

See the main skill body, golden rule 3 — patterns
(`source conda.sh; conda activate <env>` vs direct binary path) apply
identically. The non-obvious rules, repeated tersely:

- `export PYTHONUNBUFFERED=1` always (logs flush).
- **Never** `conda run -n <env> python` (subprocess pipe buffers
  stdout even with `python -u`).
- **No `set -u`** (conda activation refs unset vars like
  `$ADDR2LINE`, `$AR`, `$CC` and aborts).

## Solver speed: libmamba is the default

`mamba` (or recent `conda` with the libmamba solver, default since
conda 23.10) solves dependencies much faster than classic conda for
large scientific stacks. `miniforge3` ships libmamba by default;
verify with `conda info | grep -i solver`. If you're on classic and
solves are slow, switch via `conda config --set solver libmamba`.

## Per-project env composition

This reference covers the cluster-side operational story. For per-project
env composition (which envs to ship, the canonical TF/Keras/JAX stack,
when to split into 2 vs 3 vs 4 envs, the libs/ submodule + pip URL dual
install pattern) see the **cogneuro-project** skill's
`references/envs.md`.
