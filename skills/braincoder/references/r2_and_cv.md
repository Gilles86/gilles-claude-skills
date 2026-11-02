# R² and cross-validated R²: comparing models without fooling yourself

Examples: a 7T dataset, 30 subjects, fits as in `convergence.md`. Terms are labelled
generically; the lessons do not depend on the specific effects.

## Save SSE and SST, then choose the summary

Save per voxel and fold: `sse_test`, `sst_test`, plus the train equivalents. Clipped R²
cannot be pooled afterwards.

| Summary | Formula | Favours |
|---|---|---|
| Per-voxel mean | mean over voxels of `ΔSSE_v / SST_v` | low-variance voxels (small SST inflates them) |
| Pooled | `Σ_v ΔSSE_v / Σ_v SST_v` | high-variance voxels; what the optimizer minimised |

**They can disagree in sign.** Same term with the same strength, same voxels, ΔR² per
subject × ROI, median over subjects:

| Region | Per-voxel mean (×10⁻³) | Subjects > 0 | Pooled (×10⁻⁵) | Subjects > 0 |
|---|---:|---:|---:|---:|
| V1 | −0.02 | 47% | −0.36 | 7% |
| V2 | **+0.29** | 80% | **−12.6** | 27% |
| V3 | +0.05 | 50% | −1.95 | 37% |
| hV4 | +0.04 | 83% | +0.83 | 60% |
| All (per subject over ROIs) | +0.04 | 83% | −0.15 | 40% |

The per-voxel column is a mean over subjects, the pooled one a median. Decide on one
metric in advance, report it with the percentage of subjects, and treat a sign flip as a
warning that a few voxels drive the result. Use pooled when comparing models, since it
matches the loss.

### Pooled R² can be set by a handful of voxels: check first

Percent-signal-change scaling divides by each voxel's mean, so voxels with a very low raw
mean (mask edge, signal dropout) can have enormous variance. Pooled R² then describes those
voxels and nothing else. One subject, 9,894 voxels in visual and parietal ROIs, all fitted
without any voxel selection:

| Voxels kept (by test SD of the BOLD, % signal) | n | Gaussian | DoG | Gaussian + flex HRF | DoG + flex HRF |
|---|---:|---:|---:|---:|---:|
| All | 9,894 | +0.0070 | **−0.0024** | +0.0068 | **−0.0027** |
| SD ≤ 20 (drops the 10 largest) | 9,884 | +0.1022 | +0.1040 | +0.1067 | +0.1092 |
| SD ≤ 6.6 (99th percentile) | 9,795 | +0.1106 | +0.1136 | +0.1151 | +0.1189 |
| Median voxel, all | 9,894 | +0.0101 | +0.0137 | +0.0113 | +0.0165 |

- The top voxel held 51% of the total test variance and the top 10 held 90% (median voxel SD
  1.1%, largest 418%). Removing the 10 voxels turned a negative R² into 0.10 and restored the
  expected ordering.
- This looks like runaway parameters and is not: those voxels' amplitudes are large because
  their scale is large. Compute the shares before blaming the optimizer.
- The raw mean falls with SD: median 947 for SD ≤ 3, 170 for SD > 10 (mask median 777).

**Rule:** report the top-1 and top-10 share of `Σ SST` for every subject × ROI. Exclude
extreme voxels using a criterion that doesn't depend on any model (SD of the BOLD, or better,
the raw mean before scaling), and show that the conclusion survives more than one cutoff.
Selecting signal voxels doesn't solve it: in a set of at most 500 reliable voxels per ROI,
one voxel still held a median of 5.7% and up to 67% of the variance.

**Shared parameters are exposed too.** Per-voxel parameters are independent, so these voxels
only distort the summary. A parameter shared across voxels (a modulation width or gain) is
fitted to summed squared error, so such voxels can dominate its fit. Screen them before
fitting shared-parameter models.

## Restrict the comparison to voxels with signal

Use a **model-free reliability** selection: the null below, held out across runs, > 0. It
does not favour any encoding model. Half of all voxels can fail it, and they give extreme
ΔcvR²:

| Null cvR² of the voxel | ≤ 0 | 0–0.05 | 0.05–0.1 | 0.1–0.2 | 0.2–0.3 | > 0.3 |
|---|---:|---:|---:|---:|---:|---:|
| Share of voxels | 52% | 10% | 7% | 10% | 7% | 14% |
| Per-voxel mean ΔcvR² (×10⁻³), stimulus-drive term | +15.4 | +11.3 | +8.3 | +5.0 | +2.7 | +1.4 |
| Per-voxel mean ΔcvR² (×10⁻³), small location-specific term | −3.0 | −0.24 | −0.27 | −0.43 | −0.60 | −0.92 |

- Stimulus terms help most where the null is worst, because the null lacks the stimulus
  that differs between runs. This is a design property: check what your null can capture.
- Signal voxels vanish in frontal and parietal ROIs (V1 83%, V3 75%, IPS 12%, SPL1 1.7%,
  FEF 0.4%). Show n per ROI and don't interpret a median over 3 subjects.

## Which null

| Null | Prediction | Use |
|---|---|---|
| Training mean | one number per voxel; cvR² ≈ 0 | floor |
| **Cross-run mean response** | mean BOLD over training runs per within-run TR, when runs share a stimulus sequence | reproducibility ceiling, voxel selection |

A training mean computed with `.mean(axis=0)` over all TRs instead of per TR gives
cvR² ≈ 0 and a false "no signal in any voxel".

## Choose the fold by the question

| Scheme | Held out | Tests | Watch out |
|---|---|---|---|
| Leave one condition out | all runs of a condition | transfer to an unseen condition | A condition-specific term must generalise to a condition it never saw; penalty concentrates where the term acts |
| Leave one run per condition out | one run of each condition | prediction with all conditions in training | Folds mix conditions, so per-voxel results can't be split by condition unless re-predicted per run |
| Leave one subject out | no fit on the subject | is the *population value* useful | See below |
| Any | | | **Warm starts must not have seen held-out data:** rerun the seed chain inside each fold |

Percentage of subjects whose prediction improves for the same six terms:

| Term | Leave one condition out | Leave one run per condition out | Leave one subject out, zero parameters |
|---|---:|---:|---:|
| Stimulus-drive term | 100 | 96 | 100 |
| Target-locked gain | 73 | 65 | 90 |
| Sustained gain | 83 | 77 | 87 |
| Distractor-locked gain | 23 | 27 | 50 |
| Small location-specific term A | 20 | 35 | 80 |
| Small location-specific term B | 7 | 12 | 73 |

(Second column preliminary, 26 of 30 subjects.) All numbers on the same voxels.

## A real effect can lose cross-validation

Adding a term with true value θ and per-subject estimation variance σ²_θ changes the expected
held-out SSE by about `(σ²_θ − θ²)·ΣX²`. **If |θ| < its per-subject SE, the term hurts out of
sample even when it's real.** In the example, term A had θ ≈ 0.019 and fold SD ≈ 0.044, so it
had to lose, and its penalty showed up exactly where its regressor has its energy.

So don't conclude "not in the data" from a within-subject CV loss. Check the ratio first,
then use a test with no estimation noise for that subject.

## Leave-one-subject-out, zero-parameter test

1. Fit the simpler model to each subject.
2. Compute the term's regressor: `X = ∂pred/∂θ` by central difference. Check linearity.
3. Save per voxel `a = ΣX²`, `b = ΣX·residual`, `sst`. Then `ΔSSE(δ) = δ²a − 2δb`.
4. For subject s, set δ to the median over the *other* subjects of `Σb/Σa`.
5. For modulation fields, set the width to the other subjects' median in the same way. The
   others' optima were computed at widths that include this subject's, a small leak; state it.
6. Test ΔR² across subjects (pooled per subject × ROI, signal voxels).

**Take δ from the conditional optimum `b/a`, not from a parent-and-child joint refit.** A
joint fit lets other parameters compensate, which inflates the term (median 2.9× across the 10
of 11 ROIs where the signs agreed, range 1.4–8×). Since `ΔSSE < 0` requires `|δ| < 2|b/a|`, an inflated δ overshoots and
*hurts*: the same term gave −12.6 × 10⁻⁵ in V2 with δ from the joint fit, +0.08 × 10⁻⁵ with
the conditional δ.

The result is a statement about the population, not about prediction for one subject's own
fit. Report it as such, with the effect size. In the example it was about 10⁻⁵ R².

## Quick reference

- `r2 == 1.0` exactly: phantom from mismatched indices, not a good fit. `get_rsq` raises on
  this since 0.6.2, so recompute any cvR² from older code. See `SKILL.md`.
- `r2 == -1000` or all-zero parameters (before 0.6.2), NaN (since 0.6.2): the voxel has a NaN
  sample or zero variance. Drop these before aggregating, and count how many you dropped.
- Clipping at −1 hides how bad a voxel is. Fine for a map, not for aggregation.
- In-sample R² always favours the more flexible model. Never compare models on it, and
  beware "signal voxel count at FDR" between models: it compares thresholds, not prediction.
- Also check n per ROI after every aggregation: a subject that OOM'd can vanish silently.
