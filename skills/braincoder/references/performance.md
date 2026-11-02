# Performance: hardware, backends, iterations

Measured in the benchmark for the braincoder paper (`~/git/paper_braincoder`,
`notes/data/runtime.tsv`, May 2026, Keras 3 with TF 2.20). Values are medians of 3 seeds,
in **seconds of internal fit time**. Each run is 2D Gaussian PRF + SPM HRF.

Datasets: synthetic grids of 490 / 4,900 / 49,000 voxels with T=200, and van Es 2019
(118,584 surface vertices, 93,918 non-NaN, T=120). The real-data fit used
`noise_model='gaussian'`, `r2_atol=1e-4` and at most 10,000 iterations. The synthetic
rows are 100 iterations.

## Is a GPU worth it?

| Voxels | CPU 32 | A100 | Speedup |
|---|---:|---:|---:|
| 490 | 22 | 18 | 1.2× |
| 4,900 | 51 | 19 | 2.7× |
| 49,000 | 374 | 58 | 6.4× |
| 118,584 (real, to convergence) | 15,928 | 889 | 18× |

**Below a few thousand voxels a GPU buys almost nothing**, so don't queue for one. An
ROI fit is fine on CPU. Above that, take the GPU.

## Which GPU

Real dataset, TF backend:

| Hardware | Gaussian | DN |
|---|---:|---:|
| H200 | 423 | 1,154 |
| H100 | 510 | 1,288 |
| A100 | 889 | 1,626 |
| L4 (24 GB) | **OOM** | not run |

- H200 ran last, so it may have had NaN voxels dropped before the fit where the others did
  not, and DN on A100 is a single run. Treat small differences between GPUs with caution.
- **The memory limit is the practical one.** A whole-surface fit (about 100k vertices) did
  not fit into 24 GB. For a static PRF, cost scales with voxels × timepoints × pixels,
  so smaller jobs should fit.
- The cluster's GPU inventory changes; see **sciencecluster**. V100s failed on TF 2.20
  (cuDNN) and have since been removed.
- For dynamic RF models (the RF moves every TR), the forward builds a per-TR Gaussian
  buffer and can reach about 20 GB at V=500, T≈3096, 2500 pixels. For an isotropic
  Gaussian on a rectangular grid, separating it into x and y factors with `einsum` is
  exact. In one project this took peak VRAM from over 24 GB to 642 MB and made it 13×
  faster. It helps little for static models.

## Which backend

- **Results are identical across backends and hardware**: R² matches to three decimals
  across TF and JAX on A100, H100 and H200, and across seeds. The grid + Adam pipeline
  is deterministic, so repeat seeds only to time it.
- **On GPU, the difference is small and goes either way**: JAX is faster on A100 (771 vs
  889) and H200 (371 vs 423), slower on H100 (571 vs 510). Use whichever env you have.
- **Torch has no valid benchmark rows.** Its default allocator hit OOM at about 75 of
  80 GB on the long loop due to fragmentation; set
  `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`.
- **One env per backend on GPU.** TF, JAX and torch CUDA stacks conflict.
- Laptop (Apple Silicon, one run, 500 voxels × 774 TR × 2500 pixels, s/iteration): torch
  on MPS 0.06, JAX on CPU 0.10, TF on CPU 0.19. Torch needs
  `PYTORCH_ENABLE_MPS_FALLBACK=1` for `lstsq` and `solve`.

## How many iterations

Real dataset, A100, SSQ loss, default `r2_atol` (the sweep predates the Gaussian loss):

| Max iterations | 10 | 100 | 300 | 1,000 | 3,000 | 10,000 |
|---|---:|---:|---:|---:|---:|---:|
| Mean R² | 0.149 | 0.155 | 0.182 | 0.211 | 0.216 | 0.219 |
| Median R² | 0.042 | 0.054 | 0.084 | 0.092 | 0.096 | 0.099 |
| Seconds | 50 | 79 | 140 | 357 | 964 | 3,108 |

So about 0.3 s/iteration here, and the gains are nearly exhausted by 1,000–3,000.

- **Use `r2_atol=1e-4` on large real data.** The default 1e-6 is unreachable: improvement
  per 100 iterations plateaus around 1e-5, so it runs to the iteration cap. 1e-4 stops
  near iteration 3,000, about 3× faster, for a cost of under 0.001 in R².
- **Gradient descent matters on real data but not on clean synthetic data.** Grid + OLS
  to full fit: mean R² 0.149 → 0.216 on van Es, 0.280 → 0.275 on a synthetic grid with a
  denser search. A synthetic benchmark will understate what it does.
- **Loss:** `'gaussian'` costs about 1.2× per iteration but needs about 5× fewer
  iterations on heteroskedastic data (50 voxels, synthetic; θ-RMSE at 1,000 iterations
  0.54 vs 2.81 for `'ssq'`; the two agree by 20,000).

## Extras and their cost

- **Flexible HRF is expensive and can matter.** On A100: 303 vs 58 s (49k voxels, 100
  iterations); CPU 32: 4,059 vs 374. On van Es, mean R² went 0.216 → 0.316, median 0.096 →
  0.242. On CPU it does scale with cores: 49k voxels took 11,110 s on 8 cores, 6,995 on
  16, and 4,059 on 32.
- **DN** costs about 2–3× a Gaussian on the same GPU.
- **Grid search** barely scales with CPU threads: 49k voxels took 550 / 458 / 376 s on
  8 / 16 / 32 cores. For chunking, `ParameterFitter(memory_limit=…)` sets the chunk size;
  lower it on OOM.
- **Parameter recovery on synthetic data** (49k voxels): x, y r≈0.965 for every package;
  `sd` is the weak one (r≈0.5 here, 0.66 for AFNI and popeye) and biased low. Do not read
  much into single-voxel `sd`. A flexible HRF improves its bias (−0.85 → −0.71).

## Scaling a CPU job

Pin threads to the allocation, or `cpu8` and `cpu32` jobs behave alike:

```bash
export CUDA_VISIBLE_DEVICES=""
export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK MKL_NUM_THREADS=$SLURM_CPUS_PER_TASK
export TF_NUM_INTRAOP_THREADS=$SLURM_CPUS_PER_TASK TF_NUM_INTEROP_THREADS=2
```

## Measuring your own env

```bash
PYTHON=$HOME/data/conda/envs/<env>/bin/python sbatch --account=<acct> --partition=<cpu-partition> \
    --cpus-per-task=16 scripts/bench_fit.sh
PYTHON=… sbatch --account=<acct> --partition=<gpu-partition> --gres=gpu:1 --constraint=<gpu> scripts/bench_fit.sh
```

`bench_fit.sh` does not set the backend, so export `KERAS_BACKEND` yourself in a Keras 3
env, and record `braincoder.__version__` next to the results. **Only compare rows from the
same braincoder code path.** A pre-Keras TF fork compiles with `tf.function`, while the
Keras 3 port runs eagerly, so timings from one say little about the other. Timing also
varies by node, so run a few repeats before concluding that more CPUs made a job slower.

## The pre-Keras TF line (`tf.function`, `feature/f-beta-r2-mixture`)

Some projects pin this older code path, which compiles the training step, so **don't compare
these rows with the Keras 3 tables above.** Measured 2026-11-02 with `scripts/bench_fit.py`
(random binary paradigm, 2500 pixels, TF 2.14), one run each.

Seconds per Adam iteration, Gaussian with fixed HRF:

| Voxels | T | CPU 8 | CPU 16 (slow node) | CPU 32 |
|---:|---:|---:|---:|---:|
| 500 | 774 | 0.020 | 0.11 | 0.018 |
| 2,000 | 774 | 0.062 | 0.25 | 0.035 |
| 10,000 | 774 | 0.23 | 1.32 | 0.15 |
| 50,000 | 774 | 0.89 | 7.04 | 0.74 |
| 500 | 3,096 | 0.041 | 0.22 | 0.025 |
| 2,000 | 3,096 | 0.15 | 0.85 | 0.079 |
| 10,000 | 3,096 | 0.62 | not reached | 0.32 |
| 50,000 | 3,096 | 2.7 | not reached | 1.7 |

- **The node matters more than the core count.** 8 → 32 cores gained 1.1–2×, while one
  16-core job on another node was 4–8× slower than the 8-core job. I don't know why (load or
  CPU type); rerun on another node before concluding anything from a slow job.
- **Cost is about linear in voxels and in T**, and DoG adds only about 20% per iteration
  (0.27 vs 0.23 s at 10,000 voxels, T=774, CPU 8; flexible HRF and DN rows are still pending).
- **Memory:** DoG with V=50,000 × T=3,096 was killed at `--mem=64G` on both CPU jobs that
  reached it; the same size Gaussian passed. Split voxels into chunks well below that.

A fit on real data, per fold, 8 CPUs: **400 voxels × 2300 TRs of a modulation-field model
took 28 min of Adam (90th percentile 58 min) for the per-voxel pRF stage, then 1.5–2 min of
L-BFGS per shared-term model.** Dynamic-field forwards cost far more per voxel than the
static rows above. Loading the BOLD adds 4 min per subject (about 270k mask voxels × 12 runs)
if you mask after loading the full brain, so cache ROI data when you loop over ROIs.
