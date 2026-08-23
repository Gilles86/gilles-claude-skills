# Posterior predictive checks (PPCs)

**When to load:** plotting a posterior predictive check — overlaying a
model's simulated data on the observed data to judge fit. Common for
psychometric/chronometric curves, RT distributions, choice
proportions, or any "does the model reproduce the data" panel from a
`bauer` / PyMC / NumPyro / Stan fit. Pairs with
`bayesian_posteriors.md` (that one is for *parameter* posteriors; this
one is for *predicted data*).

## The one rule that matters

**Observed data is the anchor (points/markers); the model is the
overlay (line + shaded credible band) — never the reverse.** The eye
should land on the data first and read the model as "how well does
this curve+band cover those points." A PPC where the model is drawn as
prominent points and the data as a faint line has the visual hierarchy
backwards and reads as if the simulation were the measurement.

- **Data**: markers (filled circles), the strongest ink. If the data
  summary itself has uncertainty (across-subject SEM of a binned
  proportion), thin error bars on the points are fine — but keep them
  visually subordinate to the model band.
- **Model**: posterior-predictive **median** as a line, **95% HDI** as
  a shaded band behind it (`alpha` ~0.2–0.25, no edge), optionally a
  darker **50% HDI** inner band. Same hue as the condition.
- One color per condition, consistent with the rest of the figure
  (color is semantic across panels — see the main skill).

## The point of a PPC is to expose misfit, not hide it

A PPC that's been smoothed/aggregated until the model always covers the
data has been robbed of its function. Bin at a resolution that can
still *show a discrepancy*; put the data points where the model is
weakest (tails, fastest RTs, extreme stimulus levels) on the plot, not
averaged away. A good PPC panel earns its place by either building
trust (band covers data across the range) or pointing at the failure
(data sits outside the band somewhere specific) — annotate that
failure directly ("Model underpredicts fast errors").

## Before you build one: the two questions that catch most PPC bugs

Answer both in writing before plotting. Each has a cheap numeric test.

**1. Is the band built from SIMULATED OUTCOMES, or from predicted probabilities?**

It must be simulated outcomes. Aggregating the model's `p` gives the posterior of the
*mean probability* — parameter uncertainty only. The observed proportion additionally
carries trial-level sampling noise, so a `p`-based band is far too narrow and ordinary
scatter reads as misfit. For a Bernoulli outcome:

```python
sim = (rng.random(p.shape) < p).astype(float)   # NOT p itself
```

*Test — band coverage.* For a nominal 95% band, roughly 95% of observed points should
fall inside it. Compute `((obs >= lo) & (obs <= hi)).mean()`. Well below 0.95 means the
band is too narrow (usually this bug); well above means it has been over-smoothed and
the check can no longer fail. **Print this number every time.**

**2. Is the model aggregated exactly as the data are?**

Same grouping keys, same order of operations, and the per-draw statistic computed
*before* summarising across draws. Averaging over subjects must happen **within** each
posterior draw.

*Test — feed the raw data through the model's pipeline.* Replace the simulated outcomes
with the observed 0/1 choices as if they were a single draw. If the two paths are truly
identical, this reproduces the observed summary to machine precision:

```python
fake = observed.values[:, None]                  # one "draw"
via_model_path = (pd.DataFrame(fake, index=idx).groupby(level=keys).mean()
                    .groupby(group_keys).mean())
assert np.allclose(via_model_path.iloc[:, 0], observed_summary, atol=1e-12)
```

Anything above ~1e-12 means the pipelines differ — usually different grouping keys, a
dropped subject, or a binning step applied on one side only.

**A third trap, upstream of both:** if the predictor is binned, bin on a *rank*
(`v.rank(method='first')`) whenever it has few distinct values. `qcut` on a tied
variable splits differently across pandas versions and silently changes the figure
between machines.

## How to build it (the aggregation that keeps PP uncertainty)

The band must propagate posterior-predictive uncertainty, so compute
the summary statistic **per posterior-predictive draw**, then take the
HDI across draws — do **not** collapse pp draws to a mean first.

```python
# ppc: long DataFrame with one row per (trial, pp_draw): simulated outcome + predictor + condition
# 1. bin the predictor (shared bins for data and model)
df['bin'] = pd.qcut(df['x'], q=9, labels=False, duplicates='drop')
binx = df.groupby('bin')['x'].mean()

# 2. DATA: observed summary per bin (per condition)
data = (df.groupby(['condition', 'bin'])['observed']
          .mean().reset_index())
data['x'] = data['bin'].map(binx)

# 3. MODEL: summary per (bin, pp_draw), THEN HDI across draws
per_draw = (ppc.groupby(['condition', 'bin', 'pp_draw'])['simulated']
              .mean().reset_index())
def hdi(v):
    lo, hi = az.hdi(v.values, hdi_prob=0.95); return pd.Series({'lo': lo, 'hi': hi})
model = (per_draw.groupby(['condition', 'bin'])['simulated']
           .agg(median='median').join(
            per_draw.groupby(['condition', 'bin'])['simulated'].apply(hdi).unstack())
           .reset_index())
model['x'] = model['bin'].map(binx)
```

Then plot data points over model band:

```python
for cond, col in palette.items():
    m = model[model.condition == cond].sort_values('x')
    d = data[data.condition == cond].sort_values('x')
    ax.fill_between(m['x'], m['lo'], m['hi'], color=col, alpha=0.22, lw=0, zorder=1)
    ax.plot(m['x'], m['median'], color=col, lw=1.3, zorder=2)
    ax.plot(d['x'], d['observed'], 'o', color=col, ms=4, mec='white', mew=0.5, zorder=3)
    ax.text(d['x'].iloc[-1], d['observed'].iloc[-1], '  ' + cond.capitalize(), color=col, va='center')
```

Direct-label conditions on the data (no legend) per the house style.

## From a fit to PPC draws

- **bauer**: `model.ppc(paradigm, idata, n_posterior_samples=200)`
  returns a long DataFrame indexed by (trial keys, pp sample) with a
  `simulated_choice` (and `simulated_rt` for DDM/RDM) column — already
  the shape above. Merge the predictor/condition columns back on by the
  trial keys. `model.predict(paradigm, parameters)` gives the per-trial
  model `p_choice` for a single parameter set (loop posterior draws for a band).
  - **Trace → parameters** (the "give it the trace, get the parameters"
    extractors): `model.get_groupwise_parameter_estimates(idata, include_sd=True)`
    → population `{param}_mu` coefficients (with regressor coords, e.g.
    `width_z`, `C(group)[..]`) + `_sd` spreads; `get_subjectwise_parameter_estimates(idata)`
    → per-subject draws. Use these instead of re-parsing summary TSVs.
  - **DO NOT** pass `save_p_choice=True` to `build_estimation_model`, or
    `save_trialwise_estimates=True` to the regression model constructor
    (e.g. `PsychometricRegressionModel(...)` — checked against `bauer/core.py`
    and `bauer/models/ddm.py`: the two flags live on different objects, not
    both on `build_estimation_model`), just to get a PPC: either one writes a
    deterministic **per trial × per draw × per chain** into the idata and
    balloons it to GBs on trial-rich datasets. Recompute trialwise quantities
    **on demand** with `ppc`/`predict` from the compact trace instead.
- **PyMC**: `pm.sample_posterior_predictive(idata)` →
  `idata.posterior_predictive[<obs>]` with dims (chain, draw, obs) →
  `.to_dataframe(name='simulated').reset_index()` directly, **no** `.stack((chain,
  draw))` first — verified that raises `ValueError: cannot insert draw,
  already exists` (xarray puts `chain`/`draw` in the stacked frame both as
  index levels and as their own columns, so `.reset_index()` collides with
  itself). The unstacked call gives columns `chain, draw, obs, simulated`
  directly; group by `['chain', 'draw']` (or add
  `df['pp_draw'] = df.groupby(['chain', 'draw']).ngroup()` for a single id)
  instead of relying on a combined `pp_draw` from the stack.
- 200 pp draws is plenty for a smooth 95% band; more just slows the
  plot.

## The standard PPC panel types

- **Psychometric PPC** (choice vs stimulus): x = stimulus / decision
  variable (binned), y = P(response); data points + model band, one
  series per condition. Chance line at 0.5 (thin gray dashed).
- **Chronometric PPC** (RT vs stimulus): same layout, y = mean or
  median RT. Often paired beneath the psychometric sharing the x-axis.
- **RT distribution PPC**: overlay the observed RT histogram (or KDE)
  with model-simulated RT density; or, better for decision models, a
  **quantile-probability plot** (RT quantiles — .1/.3/.5/.7/.9 — on y,
  response proportion on x, correct vs error). Show data quantiles as
  markers, model quantiles as lines/bands. Split correct vs error
  responses (errors are where DDMs most often misfit).
- **Defective CDFs / cumulative RT** for two-choice RT: cumulative
  distribution per response, scaled by that response's probability.

## Per-subject vs group PPCs

- **Group PPC**: aggregate the binned statistic across subjects
  (compute per-subject-per-bin first, then across-subject mean for the
  data points; the model band already carries pp uncertainty). State
  in the caption that points are across-subject means.
- **Per-subject PPC**: a `FacetGrid` with one small panel per subject
  is the honest way to show the model fits *individuals*, not just the
  grand mean (a model can fit the average and miss every subject). Use
  it when individual fit is part of the claim; shared axes across
  panels.

## Caption language

- "Points: observed data (across-subject means). Line and shaded band:
  posterior-predictive median and 95% HDI."
- Say "posterior predictive", and "HDI"/"credible", never "confidence".
- If data are binned, state the binning ("9 quantile bins of the
  decision variable") — a reader can't otherwise tell signal from
  binning artifact.

## The mean-parameter trap (this one is easy to miss and looks plausible)

**A curve evaluated at the mean parameters is not the mean of the curves.** For any
nonlinear link — and every psychometric, tuning curve, softmax and sigmoid is one —

    f(E[theta])  !=  E[f(theta)]

so a "model fit" drawn by plugging the posterior-mean parameters into the link does
**not** predict the statistic you plotted the data as. If the observed points are an
average across subjects, the model line must be the same average across subjects, taken
*after* evaluating the link per subject (and per draw).

The failure is directional and therefore easy to mistake for real misfit: averaging
sigmoids whose thresholds differ **flattens** the average, so the mean-parameter curve
is always **too steep**. It will sit below the data at the low end and above it at the
high end, exactly like a model that over-predicts the effect of the stimulus.

Measured on one real hierarchical probit (35 subjects, 6 bins, 2 conditions, 2 orders):
mean-parameter curve RMSE **0.069**, correctly aggregated prediction RMSE **0.019** — a
3.7x difference that reads as "the fit is bad" rather than "the plot is wrong".

Correct order of operations, always:

```python
# WRONG -- link applied to averaged parameters
p_line = expit(slope.mean() * (x - threshold.mean()))

# RIGHT -- link per subject per draw, then aggregate the same way the data were
p = expit(slope[:, :, None] * (x[None, None, :] - threshold[:, :, None]))  # draw, subj, x
p_subj_avg = p.mean(axis=1)              # average over subjects, matching the data
line = np.median(p_subj_avg, axis=0)     # summarize draws AFTER aggregating
band = np.quantile(p_subj_avg, [.025, .975], axis=0)
```

The same trap applies to any derived quantity summarized from a posterior: a ratio of
means is not the mean of ratios, `|dP/dm|` at the mean is not the mean `|dP/dm|`, and a
credible interval for a product cannot be built from the two marginal intervals. If a
figure invites the reader to multiply or divide two plotted panels, check that the
arithmetic actually holds on the aggregated values before saying so in the caption.

**Cheap check:** compute RMSE of your model line against the plotted points. If it is
much worse than the model's own reported fit, suspect this before suspecting the model.

## Anti-patterns

- Plotting the **mean of pp draws as a line with no band** — throws
  away the predictive uncertainty that makes a PPC interpretable.
- Collapsing pp draws to a mean *before* binning/aggregating (compute
  the statistic per draw, then summarize — order matters for the band).
- Model drawn as bold markers, data as a thin line (hierarchy
  reversed).
- Different bins for data vs model (the discrepancy you see is then
  partly a binning artifact). Use shared bins.
- Over-binning until everything fits — a PPC that can't fail isn't a
  check.
- **Drawing the link function at the posterior-mean parameters** and
  calling it the fit — see "The mean-parameter trap" above. Always
  evaluate per subject/draw and aggregate the way the data were
  aggregated.
