# Decoding with braincoder

A posterior is only as good as its noise model. A misspecified Ω can give a reasonable
posterior *mean* and badly overconfident *widths*, so check calibration on held-out
trials before reading posterior SD as "uncertainty". Full argument:
`docs/noise_models.rst` in the braincoder repo.

## Which noise model

| Noise model | Use for |
|---|---|
| `LowRankNoise` (0.6+) | **Default** when you interpret posteriors and have several training runs. Rank `k` and temperature `T` are chosen by nested, run-grouped CV on the decoding objective |
| `ResidualFitter` | Reproducing old pipelines and comparing with the literature (van Bergen et al. 2015) |
| Diagonal: `np.diag(residuals.var(0))`, or `LowRankNoise(k=0)` | Baseline, few voxels |

Why `ResidualFitter` is no longer the default, from 7T single-trial betas (19 participants):

- Its Ω has **one** shared factor. Held-out squared Mahalanobis distances were about 4×
  too large (about 16× along decoding directions), every participant scored worse than a
  flat posterior, and 95% HDI coverage was 0.79.
- **`lambd` shrinkage is unsafe when voxels > trials**: coverage about 0.04 at `lambd=0.5`.
- `init_pseudoWWT` builds WWᵀ from raw predictions, so the common-mode response dominates it.

On simulated data `ResidualFitter` can look fine. In a clean simulation with independent
noise it reached coverage of 0.5 / 0.95. Good simulation results do not transfer here;
check on the real data.

The nested CV chose k=0 in about 60% of folds and T≈360 (median) on that dataset. **T ≫ 1
means there is little calibrated stimulus information**; report it rather than hiding it.
Always report `noise.summary()`.

## Recipe

```python
from braincoder.noise import LowRankNoise
from braincoder.utils.calibration import calibration_summary, plot_calibration

grid = np.linspace(0, 40, 81).astype(np.float32)     # the prior: see below
noise = LowRankNoise.fit(model, train_data, train_paradigm, pars,   # training data ONLY
                         stimulus_range=grid, groups=train_runs)    # groups = runs
pdf = model.get_stimulus_pdf(test_data, grid, parameters=pars, noise_model=noise)
print(noise.summary())
calibration_summary(pdf, test_stimuli)   # log_score, coverage_0.5/0.95, pit_sd (≈.289), r_posterior_mean
plot_calibration(pdf, test_stimuli)
```

- **`groups=` matters.** Trials within a run share noise; without it, `n_folds`
  contiguous blocks are used.
- **`inner_parameters`.** By default the encoding parameters stay fixed in the inner
  folds. Those trials helped fit them, so T may come out a little small. Pass a dict
  `{group: parameters}` from existing leave-one-run-out fits, or a refit callable, for
  the clean version.
- **`k` selected by decoding, not by covariance fit.** The covariance likelihood keeps
  asking for more factors (to k=160) while decoding worsens beyond k≈40.
- Training stimuli are matched to the nearest grid point, with a warning if they are
  more than half a step away. Use a fine enough grid.
- **Legacy code path:** `omega, dof = fit_lowrank_omega(residuals, k=40)`, then
  `get_stimulus_pdf(data, grid, omega=omega, dof=dof, temperature=T)`, or
  `noise.to_dense()`.

## With `ResidualFitter`

```python
model = GaussianPRF(paradigm=train_paradigm)
model.init_pseudoWWT(grid, pars)        # required without weights, else ValueError
fitter = ResidualFitter(model, train_data, train_paradigm, parameters=pars)  # writes model.parameters
omega, dof = fitter.fit(method='t', init_dof=10., max_n_iterations=1000)
pdf = model.get_stimulus_pdf(test_data, grid, parameters=pars, omega=omega, dof=dof)
```

- With weights, pass `weights=` instead of calling `init_pseudoWWT`.
- `fitter.fitted_omega_parameters` holds `tau, rho, sigma2, dof`; `fitter.n_failed_steps`
  counts rolled-back steps. Look at them. Ω = ρ·ττᵀ + (1−ρ)·diag(τ²) + σ²·WWᵀ is
  regularized, so raw-sample-covariance rank worries (T ≲ V) do not apply to it. ρ near 1
  is the near-singular case.
- It raises `ValueError` on NaN residuals (drop those voxels) or an empty voxel selection, and
  `RuntimeError` after 50 consecutive failed steps.
- `use_wwt=False` strips the σ²·WWᵀ term; `D=` adds a distance-dependent term
  (`examples/01_decoding_pipeline/02_geodesic_decoder.py`). `spherical=True` fits a
  single-scale Ω.
- `get_stimulus_pdf(omega=…)` uses `safe_cholesky` with adaptive jitter, as does a model
  constructor since 0.6.2 (before that, the constructor raised `LinAlgError` on a near-PSD matrix).

## The grid is the prior

`stimulus_range` is the support of a flat prior, with no separate prior argument.

- **Truncation fakes precision and bias.** In a test, narrowing the grid from 0–40 to
  15–25 halved the posterior SD (0.85 → 0.43). Stimuli near the edge get truncated
  posteriors, and expected-value decoding regresses toward the center. Extend the grid
  beyond the stimulus range when you interpret width or bias, or test explicitly.
- A wide-prior control only needs `get_stimulus_pdf` to be rerun if Ω and the parameters
  are cached (below).
- Normalization integrates over the grid value, so a non-uniform grid remains a flat
  density on the stimulus axis.
- 2D stimuli return an unnormalized table unless you request
  `include_multidimensional_stimulus_index=True`; use `utils.calibration.marginalize` to
  get marginals.

## Cache the intermediates

Write Ω (or the `LowRankNoise` parts), `dof`, weights and the per-fold parameters to
disk, keyed by `(subject, session, fold, model)`, in addition to posterior summaries. A
new prior, grid or readout then takes minutes. Without the cache, one wide-prior control
required refitting 32 sessions.

## Checklist before believing a decoding result

1. The voxel selection and noise model saw training trials only.
2. `parameters=` and `dof=` were passed explicitly, and each fold used its own.
3. The model is non-HRF and fitted on the same kind of data you decode.
4. `calibration_summary` on held-out trials: coverage near nominal, `pit_sd` near 0.289.
5. Shuffled labels give r≈0. r well above 0 under shuffling means leakage.
6. Check whether the result depends on the grid range.
7. For stimuli confounded with something the region encodes (orientation fixing value,
   numerosity fixing area), an above-chance r does not yet identify the dimension.
