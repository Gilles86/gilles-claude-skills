# Posteriors from PyMC / bauer: credible intervals

**When to load:** plotting posterior samples from `bauer`, PyMC,
NumPyro, or Stan — anything that gives you `arviz.InferenceData` and
you want a seaborn-style line + shaded credible band, or a forest
plot of per-subject posteriors.

Bayesian posteriors are first-class in this tradition. The convention is:

**Posterior median (or mean) as the central line, 95% HDI as a
shaded band, and 50% HDI as a darker inner band when the figure can
carry it.** Always say "credible interval" or "HDI", never
"confidence interval", in the caption — these are different objects
and the audience for this work cares.

A practical aside: **HDI ≠ equal-tailed interval** for skewed
posteriors. The highest-density interval is the shortest interval
containing the specified probability mass; the equal-tailed interval
is the 2.5%–97.5% quantile range. They coincide for symmetric
posteriors but diverge for skewed ones (variance components, bounded
parameters, log-scale parameters). For `bauer` hierarchical
posteriors, prefer HDI by default — it's the more honest summary
when distributions are skewed.

## Plotting posterior samples with seaborn

Seaborn 0.12+ added an `errorbar` parameter that accepts either a
built-in method name or a custom callable. Both options are useful:

**Option 1 — equal-tailed (percentile) intervals via the built-in
`"pi"`.** Simplest if equal-tailed is acceptable. Works directly when
posterior samples are in long form (one row per draw × x-value):

```python
# df_post has columns: 'draw', 'x', 'posterior_value'
sns.lineplot(
    data=df_post,
    x='x',
    y='posterior_value',
    estimator='median',
    errorbar=('pi', 95),         # 2.5–97.5 percentile band
    err_kws={'alpha': 0.25, 'linewidth': 0},
)
```

**Option 2 — true HDI via a custom callable using ArviZ.** The right
choice for skewed posteriors:

```python
import arviz as az

def hdi_95(x):
    lo, hi = az.hdi(x.values, hdi_prob=0.95)
    return lo, hi

sns.lineplot(
    data=df_post,
    x='x',
    y='posterior_value',
    estimator='median',
    errorbar=hdi_95,
    err_kws={'alpha': 0.25, 'linewidth': 0},
)
```

For nested HDI bands (50% + 95%), call `lineplot` twice on the same
axes — once with `hdi_50`, once with `hdi_95` — and use a slightly
darker alpha for the inner band. Plot 95% first so it sits behind 50%.

## Going from an InferenceData object to a long-form DataFrame

`bauer` returns `arviz.InferenceData`. Seaborn wants long form. The
conversion idiom:

```python
import arviz as az
import xarray as xr

# Suppose `idata` is the InferenceData returned by bauer/PyMC, and `mu` is the
# posterior variable indexed by an x-coordinate (e.g., stimulus level).
post_mu = idata.posterior['mu']                      # dims: chain, draw, x
df_post = (
    post_mu
    .stack(sample=('chain', 'draw'))                 # collapse chain × draw
    .to_dataframe(name='mu')
    .reset_index()
)
# df_post now has columns: x, chain, draw, sample, mu — long form, plot-ready
```

For posterior *predictive* draws over a fine x-grid (e.g., a smooth
psychometric curve with credible bands), generate predictions at,
say, 200 x-values inside the model and run the same conversion.
Seaborn will aggregate over the `sample` index automatically when you
map `x` and `y='mu'`.

## Discrete posteriors (per-condition parameter posteriors)

When the posterior is over discrete conditions (e.g., per-subject
parameter estimates), the equivalent of the lineplot-with-HDI is a
pointplot or custom forest plot. Two patterns:

- **Pointplot with HDI errorbars**:
  `sns.pointplot(data=df_post, x='condition', y='theta', estimator='median', errorbar=hdi_95)`.
  Works well when conditions are few and the message is about means.
- **Forest plot** (one row per subject/condition, horizontal HDI
  segments): drop to matplotlib.
  `ax.hlines(y=subject_ids, xmin=hdi_low, xmax=hdi_high, lw=1.5)` for
  the 95% segment, then a thicker overlay for the 50%, then a marker
  at the median. ArviZ has `az.plot_forest()` but its defaults don't
  match this style; either restyle it heavily with the rcParams in
  the main skill or build the forest plot manually for fine control.

## Caption language for posteriors

State the error metric precisely:

- "Shaded bands show 95% highest-density credible intervals over posterior samples."
- "Error bars show 95% HDI; points are posterior medians."
- "Inner and outer bands show 50% and 95% HDI."

Don't write "95% CI" without qualification — readers will read it as
confidence interval. Either spell out "credible interval" or use
"HDI".
