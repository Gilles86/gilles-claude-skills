---
name: braincoder
description: What braincoder is and how to use it — the Python library for fitting encoding models to fMRI (population receptive fields for visual space, numerosity, value, orientation; Keras 3 on TensorFlow, JAX or PyTorch) and inverting them for Bayesian decoding. Has a step-by-step manual for new projects, then the silent traps, including those fixed in 0.6.2 that still affect older checkouts and old results (index alignment that made R² exactly 1, one NaN sample zeroing a voxel, *WithHRF models decoding wrongly, `dof` not remembered) and those that remain (stale `model.parameters`, the wrong Keras backend), choosing a decoding noise model (`LowRankNoise` vs `ResidualFitter`) and checking calibration, voxel selection with the R² mixture, measured runtimes per GPU, CPU and backend, and writing custom models. Read it BEFORE writing or debugging any braincoder code, and when asked what braincoder is, what it has been used for, how to install or cite it, or whether a project should use it. Use whenever code touches `braincoder`, `ParameterFitter`, `WeightFitter`, `ResidualFitter`, `LowRankNoise`, `StimulusFitter`, `BayesianParameterFitter`, `GaussianPRF*`, `get_stimulus_pdf`, `fit_r2_mixture`, or `KERAS_BACKEND`; when a PRF fit is slow, stuck on CPU or out of memory; when decoded posteriors look overconfident or flat; when R² looks too good or is −1000; or when deciding what hardware or settings a fit needs. Pairs with **cogneuro-project** (where the scripts live), **sciencecluster** (running them) and **scientific-figures** (plotting the results).
---

# braincoder

## What it is

braincoder is a Python library that answers two questions about fMRI data:

1. **Encoding:** how does each voxel respond to a stimulus? You describe the stimulus,
   choose a tuning model (for example a Gaussian over visual space or over number), and
   braincoder estimates each voxel's tuning.
2. **Decoding:** given a new brain response, which stimulus most likely caused it?
   braincoder inverts the fitted model with Bayes' rule. That gives a full probability
   distribution over stimuli on every trial, so you get a best guess *and* an uncertainty.

The second part is what sets it apart from most PRF packages, which stop at the tuning
maps. The trial-by-trial uncertainty is what lets you link neural precision to behaviour.

It runs on TensorFlow, JAX or PyTorch through Keras 3, so one fit can use a GPU and
handle a whole cortical surface: about 94,000 vertices took 7–15 minutes on a recent
GPU in the paper benchmark.

| Use it for | Look elsewhere for |
|---|---|
| Tuning to a continuous stimulus: position, number, value, orientation | Plain contrasts and mass-univariate GLMs (nilearn, SPM) |
| Trial-wise decoding with calibrated uncertainty | Single-trial betas themselves (GLMsingle, then bring them here) |
| Your own tuning function, without writing an optimizer | Non-fMRI data: untested for anything else so far |
| Whole-brain PRF mapping on a GPU | Cognitive models of behaviour (**bauer**) |

## What it has been used for

| Question | Paper |
|---|---|
| Risk aversion arises from noisy magnitude codes in parietal cortex | de Hollander, Barretto-García et al. 2023, *Nat Hum Behav*, "Individual risk attitudes arise from noise in neurocognitive magnitude representations" |
| Decoded parietal payoff representations predict choice noise and bias | de Hollander et al. 2026, *Nat Commun*, "Rapid changes in risk attitudes originate from Bayesian inference on parietal magnitude representations" |
| Number tuning adapts to the stimulus range across parietal cortex | de Hollander, Prat-Carrabin et al., *Nat Commun* in press, "Distributed range adaptation in human parietal encoding of numbers" |
| TMS over parietal cortex changes risk preferences | "Risk preferences causally rely on parietal magnitude representations", bioRxiv |
| Stress, dyscalculia | "Acute stress reduces risk-aversion by changing magnitude perception"; "Domain-specific and domain-general signatures of dyscalculia…", both bioRxiv |
| Value code in orbitofrontal cortex | Le Bouc, de Hollander et al., "A Neural Population Code for Value in Human Orbitofrontal Cortex", bioRxiv |

It is also used in ongoing projects on learned abstract value, two simultaneous
numerosities, visual attention and suppression, and reward capture. Spatial Bayesian
priors for PRFs (Daghlian et al. 2025) were built as a braincoder fork. Knapen's
`prfmodel` (NL eScience Center) was inspired by it. Other users include groups in
Amsterdam, Boston, Marseille, Melbourne and Paris.

## Who and where

- **Maintainer:** Gilles de Hollander, University of Zurich, who wrote nearly all of the
  code. **Authors:** de Hollander, Renkert, Ruff, Knapen. License: MIT.
- **Code and issues:** <https://github.com/Gilles86/braincoder>
- **Documentation:** <https://braincoder-devs.github.io/> (tutorial lessons 1–7 and a
  gallery of examples; start with the lessons). It may lag a release: on 2026-11-02 it
  showed 0.6.0 while the code was already at 0.6.1. Rebuild it with `scripts/publish_docs.sh`.
- **Cite:** de Hollander, G., Renkert, M., Ruff, C. C., & Knapen, T. H. *braincoder*.
  Zenodo. DOI [10.5281/zenodo.10778413](https://doi.org/10.5281/zenodo.10778413). A
  methods paper is in preparation (benchmarks in `Gilles86/paper_braincoder`).
- **Not on PyPI.** Install from git, as below.
- **Related:** [prfmodel](https://popylar-org.github.io/prfmodel/) is another Keras 3 pRF
  package, with further models such as CSS, delayed normalization and connective fields.

This file describes **0.6.2**. Older checkouts are still in use, so rules note where old behaviour differs. The library moves quickly, so run
`python scripts/check_skill_claims.py`: it re-tests every claim here against your
installed version and tells you what changed.

## Manual: a new project in seven steps

[`scripts/quickstart.py`](./scripts/quickstart.py) is all of this as one script on
simulated data. It runs in about a minute: run it first, then swap in your data.

**1. Install.** Pin a release, so that your results stay reproducible:

```bash
pip install "braincoder @ git+https://github.com/Gilles86/braincoder.git@v0.6.2" tensorflow
```

Use `tensorflow[and-cuda]` on a GPU node, and one env per backend. Add this to every job:

```bash
export KERAS_BACKEND=tensorflow
python scripts/preflight.py --backend tensorflow --require-gpu   # prints what will actually run
```

**2. Prepare two tables** with the same index:

- `data`: one row per trial or TR, one column per voxel.
- `paradigm`: one row per trial or TR, the stimulus value in each column.

```python
data = data.loc[:, data.notna().all() & (data.std() > 0)]   # no NaN or empty voxels
assert data.index.equals(paradigm.index)                     # rows must line up
```

**3. Choose a model.**

| Your data | Your stimulus | Model |
|---|---|---|
| Single-trial betas | A number on a linear axis | `GaussianPRF` |
| Single-trial betas | Numerosity or value | `LogGaussianPRF` |
| Single-trial betas | Orientation or direction | `AxialVonMisesPRF` or `VonMisesPRF` |
| BOLD timeseries | Moving bars, visual field | `GaussianPRF2DWithHRF` |
| BOLD timeseries | Visual field with surround | `DifferenceOfGaussiansPRF2DWithHRF` or `DivisiveNormalizationGaussianPRF2DWithHRF` |

More in [Models](#models) below.

**4. Fit, in three stages.** A coarse grid search finds the rough tuning, a regression
sets amplitude and baseline, and gradient descent polishes:

```python
import numpy as np
from braincoder.models import GaussianPRF
from braincoder.optimize import ParameterFitter

fitter = ParameterFitter(GaussianPRF(paradigm=paradigm), data, paradigm)
grid = fitter.fit_grid(mu=np.linspace(5, 35, 16), sd=np.linspace(3, 15, 7),
                       amplitude=[1.], baseline=[0.], use_correlation_cost=True)
init = fitter.refine_baseline_and_amplitude(grid)
pars = fitter.fit(init_pars=init, max_n_iterations=3000, r2_atol=1e-4,
                  noise_model='gaussian', progressbar=False)
```

Grid ranges should span plausible values, with the `sd` floor no narrower than you can
believe. Keep the stimulus on a scale of roughly 1–50.

**5. Check the fit on data it has not seen.** In-sample R² (`fitter.r2`) always flatters:

```python
from braincoder.utils import get_rsq
cv_r2 = get_rsq(test_data, GaussianPRF().predict(test_paradigm, pars))
```

Fit on all runs but one, test on the left-out run. Compare with a null model that
predicts each voxel's training mean. Also simulate data from known parameters and check
that you recover them at your real noise level.

**6. Select voxels on the training data only:**

```python
from braincoder.utils.stats import fit_r2_mixture, r2_fdr_threshold
keep = train_r2 > r2_fdr_threshold(fit_r2_mixture(train_r2), .05)
```

**7. Decode the left-out run, and check the uncertainty is honest:**

```python
from braincoder.noise import LowRankNoise
from braincoder.utils.calibration import calibration_summary

stimulus_grid = np.linspace(0, 40, 81).astype(np.float32)    # extend past the stimulus range
model = GaussianPRF()                                        # never a *WithHRF model here
noise = LowRankNoise.fit(model, train_data[keep], train_paradigm, pars[keep],
                         stimulus_range=stimulus_grid, groups=train_runs)
posterior = model.get_stimulus_pdf(test_data[keep], stimulus_grid,
                                   parameters=pars[keep], noise_model=noise)
calibration_summary(posterior, test_stimuli)   # 95% interval should cover about 95% of trials
```

**Where to run it:** an ROI fit runs on a laptop or CPU. Above a few thousand voxels, use a
GPU. Loops over a whole cohort belong on the cluster, even if each subject takes under a
minute. Save parameters, weights and Ω per fold, so that a new readout needs no refit.
Write brain maps as float32 (rule 14).

## Where to read next

| About to | Read |
|---|---|
| Learn the concepts from scratch | [Tutorial lessons](https://braincoder-devs.github.io/tutorial/index.html) |
| Decode, or choose a noise model | [`references/decoding.md`](./references/decoding.md) |
| Size a job, pick a GPU or backend, set iterations, debug slowness or OOM | [`references/performance.md`](./references/performance.md) |
| Write a new model class | [`references/custom_models.md`](./references/custom_models.md) |
| Understand a model's equation and parameters, or `rf_normalization` | [`references/models_and_parameters.md`](./references/models_and_parameters.md) |
| Tell a converged fit from optimizer noise; runaway parameters; nested models | [`references/convergence.md`](./references/convergence.md) |
| Compare models with R² or cvR²; choose folds, voxels and a null; a CV loss vs a group effect | [`references/r2_and_cv.md`](./references/r2_and_cv.md) |
| Measure speed on a new env | [`scripts/bench_fit.py`](./scripts/bench_fit.py) and `bench_fit.sh` |

## The rules that prevent silent errors

Almost every failure here is silent: the fit finishes and the numbers look plausible.
Read these before you trust a result.

**1. Know which braincoder you are running.** Each project pins its own `libs/braincoder`,
and a cluster env may import a different checkout from the one you are reading. Versions
in use range from pre-Keras TF forks to the current release. Before 2026-10-19 on JAX,
`ResidualFitter` silently returned an unfitted Ω; before 2026-05-21 on TF, ν was biased
low. Refit Ω and ν from older checkouts. `scripts/preflight.py` prints the version and
path and can fail on a mismatch.

**2. Set `KERAS_BACKEND` in every job, before the first keras import.** Otherwise
`~/.keras/keras.json` decides. With `"jax"` there and a CPU-only jaxlib, a job on a GPU
node ran at 25–70 s/iteration while TF reported the GPU, so a "does TF see the GPU" check
passed.

**3. `data.index` must equal `paradigm.index`.** Since 0.6.2, `get_rsq` raises on different
labels, and the fitters pair rows by position (warning if a labelled index differed). So a
wrong row order is still your job to prevent, but it no longer hides. **Before 0.6.2 a
mismatch gave no error:**

| Mismatch, before 0.6.2 | What happened (tested on 0.6.1) |
|---|---|
| No overlap | `get_rsq` returned **R² = 1.0 for every voxel** (NaN residuals sum to 0) |
| Partial overlap, e.g. `1…n` vs `0…n-1` | `refine_baseline_and_amplitude` compared shifted timeseries; `fitter.get_rsq()` gave −0.44 where the true R² was 0.43 |

`fit()` works on arrays, so `fitter.r2` stayed correct and hid the problem. Distrust cvR² and
refined amplitudes from older versions if the indices differed.

**4. Remove NaN voxels before fitting.** A voxel with a single NaN sample, or zero variance,
cannot be fitted. It returns NaN parameters and NaN `fitter.r2`, with a warning, and
decoding with such a row raises `ValueError`. Masked voxels still cost compute (21% of the
van Es surface data were NaN). **Before 0.6.2** these voxels silently got all-zero parameters
and `fitter.r2 == -1000`, so `fitter.r2.mean()` meant nothing, and a zero row could make
every posterior NaN.

**5. Always grid, then refine, then fit.** The correlation-cost grid leaves amplitude and
baseline at your placeholder, so its raw R² is about 0 (−0.004 → 0.43 after refine). Use a
nonzero amplitude in the grid: `[0.]` makes all predictions constant, and refine raises
`not invertible` on TF or returns junk on JAX.

**6. The grid decides what width you get.** Gradient descent rarely travels far from the
grid, so a grid that offers needle widths returns needles. Raising the grid's `sd` floor
fixed one such collapse, with no need for `fixed_pars` or a prior.

**7. Keep the stimulus on a scale near 1–50, or raise the learning rate.** Adam moves about
`learning_rate` per step, so 1000 steps at 0.01 move `mu` by at most 10. Multiplying the
stimulus by 100 cut the movement from 4.8 to 0.1 in original units. Rescale a 0–900 value axis.

**8. Decode betas with the plain model, not a `*WithHRF` model.** Since 0.6.2 a `*WithHRF`
model decodes without the HRF and warns, so its amplitude must be on the scale of your
betas: parameters fitted to BOLD timeseries may not be. **Before 0.6.2** each candidate
stimulus went through the HRF as a one-sample timeseries, which shrank the tuning curve about
17× (TR 1.6 s) and made posteriors about 5× too wide, without any error. Re-decode those.
`get_fisher_information` and `get_expected_uncertainty` refuse `*WithHRF` models.

**9. Pass `omega` and `dof` together.** With an explicit `omega=`, `dof=None` means Gaussian.
Without `omega=`, both come from the model. **Before 0.6.2** `model.dof` was always ignored.

**10. Models keep state, so pass `parameters=` explicitly.** `ResidualFitter` writes
`model.parameters` and `model.weights`; `StimulusFitter` writes `model.omega` and
`model.dof`. A model reused across folds decodes with the *last* fold's parameters if you
omit them. `ParameterFitter.fit` does not set `model.parameters`: use the returned frame.

**11. Parameter order differs between models, so call `fit_grid` with keywords.** 1D is
`mu, sd, amplitude, baseline`; 2D is `x, y, sd, baseline, amplitude`.

**12. `WeightFitter` regresses through the origin by default.** A Gaussian basis can absorb a
DC offset; an all-positive linear feature gets a biased slope and can decode at r≈0. Use
`weights, intercept = fitter.fit(fit_intercept=True)` (0.6.2), or demean the data.

**13. To link the neural code to behaviour, simulate; don't use Fisher information.** Simulate
from the fitted model and noise model, then decode with an ideal Bayesian observer.
`get_expected_uncertainty` does this for 1D stimuli.

**14. Write NIfTIs through a mask with `set_data_dtype(np.float32)` and
`header.set_slope_inter(1, 0)`**, or parameters quantize to 256 values through the `uint8`
mask. See **cogneuro-project**.

## Models

| Stimulus | Class | `parameter_labels` |
|---|---|---|
| 1D, linear axis | `GaussianPRF` | `mu, sd, amplitude, baseline` |
| 1D, compressive axis | `LogGaussianPRF` | same, or `mode, fwhm, …` with `parameterisation='mode_fwhm_natural'` |
| Circular; π-periodic orientation | `VonMisesPRF`; `AxialVonMisesPRF` | `mu, kappa, amplitude, baseline` |
| Skewed | `AlphaGaussianPRF` | `mu, sd, alpha, amplitude, baseline` |
| Visual field | `GaussianPRF2D` | `x, y, sd, baseline, amplitude` |
| Polar | `GaussianPRF2DAngle` | `theta, ecc, sd, baseline, amplitude` |
| Surround | `DifferenceOfGaussiansPRF2D` | `x, y, sd, baseline, amplitude, srf_amplitude, srf_size` |
| Normalization | `DivisiveNormalizationGaussianPRF2D` | `x, y, sd, rf_amplitude, srf_amplitude, srf_size, neural_baseline, surround_baseline, bold_baseline` |
| Parameters depend on condition | `RegressionGaussianPRF`, `RegressionAlphaGaussianPRF` | one column per (parameter, regressor) |
| Fixed basis, fit weights only | `LinearModel`, or a PRF with fixed `parameters` + `WeightFitter` | |

- **Single-trial betas take a non-HRF model; timeseries take a `*WithHRF` model** with
  `hrf_model=SPMHRFModel(tr=…)`. Mixing them up gives no error.
  `flexible_hrf_parameters=True` appends `hrf_delay, hrf_dispersion`.
- **2D models:** the paradigm is `(n_t, n_pixels)` and `grid_coordinates` is
  `(n_pixels, 2)`. An aperture not flipped to match the coordinate convention still fits
  well, but lands mirrored, so check one visual-field map.
- **`rf_normalization`** (0.6.1) rescales amplitudes only: `'legacy'` (default), `'peak'`
  (prfpy's `normalize_RFs=False`), `'area'`. It matters **when you simulate**: `amplitude=1`
  gives predicted SD 0.003 in legacy and 0.04 in peak on a 20 × 20 grid, so `noise=.05`
  swamps legacy (x recovered at r=0.40) but not peak (r=0.99).
- **`allow_neg_amplitudes=True`** on 1D models, with `positive_amplitude=False` in the grid
  and refine, allows troughs. Analyse them apart from peaks, or they cancel when averaged.
- **`noise_model='gaussian'`** has the same optimum as `'ssq'`, and on heteroskedastic data
  takes about 1.2× the time per iteration but 5× fewer iterations. It becomes the default
  in 0.7, so pin `'ssq'` to reproduce old fits.
- **Refit** any DN model fitted with `flexible_hrf_parameters=True` before 0.6.1 (HRF delay
  followed the BOLD baseline).

**Basis-function workflow:** rows of `parameters` and `weights` are basis functions, and
columns of `weights` are voxels:

```python
centers = pd.DataFrame({'mu': np.linspace(0, 40, 9), 'sd': 6., 'amplitude': 1., 'baseline': 0.}).astype(np.float32)
model = GaussianPRF(parameters=centers)
weights = WeightFitter(model, centers, data, paradigm).fit(alpha=1.)
```

## Voxel selection

**Select inside the training fold.** Selecting on R² from data that includes test trials
makes decoding circular.

- `fit_r2_mixture` fits two Gaussians on logit(R²), dropping NaN and non-positive values; it
  needs at least 50 usable voxels. `r2_fdr_threshold` returns `inf` if nothing reaches α.
  `r2_posterior_signal` gives per-voxel P(signal) and is gentler on small ROIs.
- Use this mixture. Earlier methods were anti-conservative (F-test FDR) or went U-shaped and
  gave near-zero thresholds (Beta mixture).
- **cvR² favours few-parameter models.** A negative median may be just the df cost of the
  model. Compare with a label-permutation null before reporting single-voxel tuning.
- A small ROI can select 0 voxels in a fold, and `ResidualFitter` then crashes. Handle it
  explicitly, for example by keeping the top voxel.

## Other pieces

- **Stimulus reconstruction** (`from braincoder.optimize import StimulusFitter`): always pass
  `l2_norm` (start at 0.01, raise it if maps are noisy), or decoded values diverge. It needs
  TensorFlow and TFP, and the import is guarded, so without them you get `ImportError`. Adding
  TFP to a clean Keras 3 env can pull in a second TF (`undefined symbol:
  Wrapped_PyInit__pywrap_*`).
- **GP spatial prior** (`braincoder.optimize.bayesian_fitter.BayesianParameterFitter`,
  `braincoder.optimize.gp_prior.GeodesicGPPrior`; not exported at package level). Empirical
  Bayes after Daghlian et al. 2025. The Cholesky scales as O(V³), so use it on ROIs.
- **Examples:** `examples/01_decoding_pipeline/` is the current end-to-end pipeline.
  `docs/noise_models.rst` and `docs/fisher_information.rst` explain the choices.

## Working on the library itself

- Use `keras.ops`, not `tf.*`, and don't wrap what `keras.ops` already does. Test on all three
  backends (`KERAS_BACKEND=… pytest`; torch on a Mac also needs `PYTORCH_ENABLE_MPS_FALLBACK=1`).
- Never call `float()` or `convert_to_numpy` inside a loss, and never wrap an optimisation step
  in a bare `except Exception`. Together these caused the unfitted-Ω bug in rule 1.
- When adding an `__init__` argument, check it reaches the optimisation loop:
  `ResidualFitter.lambd` was silently ignored for a long time.
- Fitting runs eagerly on all backends in the Keras port (no `tf.function` or `jit`). Docs that
  mention `@tf.function` describe the pre-port code.
