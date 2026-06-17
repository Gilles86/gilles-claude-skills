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
  trial keys.
- **PyMC**: `pm.sample_posterior_predictive(idata)` →
  `idata.posterior_predictive[<obs>]` with dims (chain, draw, obs);
  stack `(chain, draw)` → `pp_draw` and `.to_dataframe()`.
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
