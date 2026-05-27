# Conda environments

Most projects use **2 envs**: a cluster CUDA env and a local
Apple-Silicon env (since the Mac side is where most dev happens, and
the cluster is where all real fits run).

- `environment_apple_silicon.yml` — top-level; conventional name
  `conda env create -f environment_apple_silicon.yml` looks for.
- `environment_cuda.yml` (or `environment_linux.yml`) — cluster GPU env.
  Sometimes lives in `create_env/`; sometimes top-level. Match what
  the project already does.

## Optional extra envs

Some projects split further. Don't add these unless you need them:

- **`environment_cpu.yml`** — separate cluster CPU env if you ever run
  CPU-only jobs on nodes where TF would mis-detect CUDA. Most current
  projects don't bother — the CUDA env runs CPU fine.
- **`environment_cuda_jax.yml`** — JAX-backend alternative to the TF
  env. Useful as a fallback if a future CUDA driver upgrade breaks
  TF; same braincoder behavior via `KERAS_BACKEND=jax`.
- **`environment_psychopy.yml`** — top-level for the experiment
  machine. PsychoPy has incompatible deps with the analysis stack, so
  isolate.

## `create_env/` — only when the build needs the cluster

If you do ship a separate CUDA env build script
(`create_env/create_gpu_env.sh`), make it an **sbatch script** so the
GPU env builds on a GPU compute node — the install verifies driver
compatibility at install time. If you don't need that (e.g. abstract_values
just keeps `environment_linux.yml` at the top level and the user runs
`conda env create -f ...` themselves on the cluster login node after
allocating a GPU `srun`), skip `create_env/` entirely.

## Canonical stack (2026-05)

Python 3.11 / 3.12 + Keras 3.13+ + TF 2.20. Verified end-to-end on
A100-SXM4-80GB with the in-house braincoder GP fitter.
`tensorflow[and-cuda]==2.20.*` (or `tensorflow==2.20.0` +
`jax[cuda12]`) bundles its own CUDA libs as pip wheels, so the env
survives `module load cuda/...` renames on the cluster.

Older TF 2.14 + Keras 2 envs (`tf2-gpu` and similar) still work for
projects that haven't migrated, but **cannot** import braincoder from
the `keras-backend` branch (it uses `from keras import ops`, a Keras 3
API). When a project upgrades, it commits to Keras 3 across all envs
simultaneously.

## Real env exemplars

- [environment_cuda.yml](environment_cuda.yml) — abstract_values cluster
  stack (TF 2.20 + jax[cuda12] + braincoder@keras-backend + GLMsingle)
- [environment_apple_silicon.yml](environment_apple_silicon.yml) — same
  versions for Mac M-series, with optional `tensorflow-metal` for GPU
