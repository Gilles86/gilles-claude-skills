# Building a posterior predictive check that can fail

**When to load:** constructing a PPC from a PyMC / NumPyro / `bauer` fit —
deciding what to simulate, how to aggregate it, and whether the resulting band
means anything. The *drawing* of the panel (visual hierarchy, labels, caption
language, panel types) belongs to the **scientific-figures** skill,
`references/posterior_predictive_checks.md`.

## The two questions that catch most PPC bugs

Answer both in writing before plotting. Each has a cheap numeric test.

### 1. Is the band built from SIMULATED OUTCOMES, or from predicted means/probabilities?

It must be simulated outcomes. Aggregating the model's `p` (or its predicted
mean) gives the posterior of the *mean* — parameter uncertainty only. The
observed summary additionally carries trial-level sampling noise, so a
`p`-based band is far too narrow and ordinary scatter reads as misfit.

```python
sim = (rng.random(p.shape) < p).astype(float)   # NOT p itself
```

For a continuous response, sample from the model's per-trial response
distribution (inverse-CDF sampling on the density grid), once per posterior
draw, producing a full synthetic dataset with the same trial structure as the
real one.

*Test — band coverage.* For a nominal 95% band, roughly 95% of observed points
should fall inside it. Compute `((obs >= lo) & (obs <= hi)).mean()`. Well below
0.95 means the band is too narrow (usually this bug); well above means it has
been over-smoothed and the check can no longer fail. **Print this number every
time**, and put it on the panel.

*How wrong it gets:* on a 26-subject, 9000-trial hierarchical fit, the
mean-based band was roughly the width of the plotted line. Every model looked
catastrophically misfit; the correctly built band showed the real coverage was
0.2–0.4, which is a different and much more specific problem.

### 2. Is the model aggregated exactly as the data are?

Same grouping keys, same order of operations, and the per-draw statistic
computed *before* summarising across draws. Averaging over subjects must
happen **within** each posterior draw.

*Test — feed the raw data through the model's pipeline.* Replace the simulated
outcomes with the observed responses as if they were a single draw. If the two
paths are identical, this reproduces the observed summary to machine precision:

```python
fake = observed.values[:, None]                  # one "draw"
via_model_path = (pd.DataFrame(fake, index=idx).groupby(level=keys).mean()
                    .groupby(group_keys).mean())
assert np.allclose(via_model_path.iloc[:, 0], observed_summary, atol=1e-12)
```

Anything above ~1e-12 means the pipelines differ — usually different grouping
keys, a dropped subject, or a binning step applied on one side only.

**A third trap, upstream of both:** if the predictor is binned, bin on a *rank*
(`v.rank(method='first')`) whenever it has few distinct values. `qcut` on a
tied variable splits differently across pandas versions and silently changes
the figure between machines.

## Why the observed points get no error band

Once the band is built from simulated datasets it already contains the
measurement noise: it *is* the distribution of datasets like the one collected.
The observed summary is a single realisation to be checked against that
distribution, not a second estimate with its own uncertainty. Drawing both
double-counts the noise, and does so in the direction that hides misfit — two
overlapping bands nearly always touch somewhere.

The temptation to add SEM bars is itself a symptom: it appears when the band
was built the narrow way and looks implausibly tight. Fix the band.

## The aggregation that keeps predictive uncertainty

```python
# ppc: long DataFrame with one row per (trial, pp_draw): simulated outcome + predictor + condition
df['bin'] = pd.qcut(df['x'], q=9, labels=False, duplicates='drop')
binx = df.groupby('bin')['x'].mean()

# DATA: observed summary per bin (per condition)
data = df.groupby(['condition', 'bin'])['observed'].mean().reset_index()

# MODEL: summary per (bin, pp_draw), THEN HDI across draws
per_draw = (ppc.groupby(['condition', 'bin', 'pp_draw'])['simulated']
              .mean().reset_index())
def hdi(v):
    lo, hi = az.hdi(v.values, hdi_prob=0.95); return pd.Series({'lo': lo, 'hi': hi})
model = (per_draw.groupby(['condition', 'bin'])['simulated']
           .agg(median='median')
           .join(per_draw.groupby(['condition', 'bin'])['simulated'].apply(hdi).unstack())
           .reset_index())
```

Check more than the central tendency. A model can match a bias curve exactly
and get the *spread* badly wrong — compute the response SD per bin on both
sides, the same way, and band it too. In practice that panel is where models
fail first.

## From a fit to PPC draws

- **bauer, estimation models** (`EstimationBaseModel` and subclasses):
  **do not use `model.ppc()` for the band.** Checked against
  `bauer/estimation.py` (2026-08): it samples only `predicted_mean` /
  `predicted_sd`, its `n_ppc_samples` argument is unused, and its "optionally
  simulates responses" docstring describes a path that is not implemented. A
  band built from what it returns is exactly the parameter-only band question 1
  warns about. Use `model.simulate(paradigm, params, n_samples=1)` once per
  posterior draw instead — it inverse-CDF samples the per-trial response
  distribution and returns a `simulated_response` column. Caveats: it draws
  through the **global** numpy RNG (seed with `np.random.seed`), and it joins
  the paradigm back on, so the observed `response` column rides along and
  collides if you rename the simulated one to `response` — drop it first.
  Check whether `simulate` applies the model's lapse rate; if it does not, the
  simulated datasets are the no-lapse model and the PPC is checking something
  the likelihood never fitted (this matters most where the fitted density is
  sharp, e.g. under a hard categorical gate).
- **bauer, choice/RT models**: `model.ppc(paradigm, idata, n_posterior_samples=200)`
  returns a long DataFrame with `simulated_choice` (and `simulated_rt`),
  already the right shape. Trace → parameters:
  `get_groupwise_parameter_estimates(idata, include_sd=True)` and
  `get_subjectwise_parameter_estimates(idata)`.
  **Do not** pass `save_p_choice=True` / `save_trialwise_estimates=True` just
  to get a PPC — either writes a deterministic per trial × draw × chain into
  the idata and balloons it to GBs. Recompute on demand.
- **PyMC**: `pm.sample_posterior_predictive(idata)` →
  `idata.posterior_predictive[<obs>]` → `.to_dataframe(name='simulated').reset_index()`
  directly, **no** `.stack((chain, draw))` first (that raises
  `ValueError: cannot insert draw, already exists`). Add
  `df['pp_draw'] = df.groupby(['chain', 'draw']).ngroup()`.
- 200 posterior-predictive draws is plenty for a smooth 95% band.

## Group vs per-subject

- **Group PPC**: compute per-subject-per-bin first, then across-subject mean
  for the data points; the band already carries predictive uncertainty.
- **Per-subject PPC**: one small panel per subject is the honest way to show
  the model fits *individuals*, not just the grand mean — a model can fit the
  average and miss every subject. The per-subject bands are wide because each
  subject has few trials per bin; that is correct, not a defect.

## The mean-parameter trap

**A curve evaluated at the mean parameters is not the mean of the curves.** For
any nonlinear link — every psychometric, tuning curve, softmax and sigmoid —

    f(E[theta])  !=  E[f(theta)]

so a "model fit" drawn by plugging posterior-mean parameters into the link does
not predict the statistic the data were plotted as. If the observed points are
an average across subjects, the model line must be the same average, taken
*after* evaluating the link per subject and per draw.

The failure is directional and therefore easy to mistake for real misfit:
averaging sigmoids whose thresholds differ **flattens** the average, so the
mean-parameter curve is always **too steep** — below the data at the low end,
above it at the high end, exactly like a model that over-predicts the stimulus
effect. Measured on one real hierarchical probit (35 subjects, 6 bins, 2
conditions): mean-parameter RMSE 0.069, correctly aggregated 0.019.

```python
# WRONG -- link applied to averaged parameters
p_line = expit(slope.mean() * (x - threshold.mean()))

# RIGHT -- link per subject per draw, then aggregate the way the data were
p = expit(slope[:, :, None] * (x[None, None, :] - threshold[:, :, None]))
p_subj_avg = p.mean(axis=1)
line = np.median(p_subj_avg, axis=0)
band = np.quantile(p_subj_avg, [.025, .975], axis=0)
```

The same trap applies to any derived quantity: a ratio of means is not the mean
of ratios, and a credible interval for a product cannot be built from two
marginal intervals.

**Cheap check:** RMSE of the model line against the plotted points. If it is
much worse than the model's own reported fit, suspect this before the model.

## Anti-patterns

- A band from predicted means/probabilities rather than simulated outcomes
- Collapsing pp draws to a mean *before* binning/aggregating
- Error bars or a bootstrap band on the observed points
- Different bins for data and model
- Over-binning until everything fits — a PPC that cannot fail is not a check
- Checking only the mean and never the spread
- Drawing the link at posterior-mean parameters and calling it the fit
