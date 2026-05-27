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

## `create_env/` — sbatch the build, but a GPU node isn't required

If you ship a separate CUDA env build script
(`create_env/create_gpu_env.sh`), make it an **sbatch script** so the
build doesn't run on the login node (ulimits + politeness — see the
sciencecluster skill's "never run compute on the login node" rule).
But you do **not** need `--gres=gpu:1` for the build itself: the
modern pip stack (`tensorflow[and-cuda]`, `jax[cuda12]`, `torch+cu*`)
ships its CUDA runtime as bundled pip wheels, so install is just
wheel extraction. Empirically verified 2026-05-27 on sciencecluster
(see `sciencecluster/references/gpu_jobs.md`). Submit the build to
`lowprio` or `standard` with no `--gres`; it's faster to dispatch
that way too.

Older `create_env/create_gpu_env.sh` scripts on legacy projects (e.g.
`tms_risk`) still ask for a GPU at build time — that was a defensive
habit from the pre-bundled-wheels era and is now unnecessary. Drop
the `--gres=gpu:1` next time you touch one of those files.

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
