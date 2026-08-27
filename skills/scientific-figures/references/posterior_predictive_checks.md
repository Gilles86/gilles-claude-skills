# Drawing a posterior predictive check

**When to load:** plotting a PPC — overlaying a model's simulated data on the
observed data to judge fit. Common for psychometric/chronometric curves, RT
distributions, choice proportions, or any "does the model reproduce the data"
panel from a `bauer` / PyMC / NumPyro / Stan fit. Pairs with
`bayesian_posteriors.md` (that one is for *parameter* posteriors; this one is
for *predicted data*).

**This file covers how the panel looks.** How the band is *built* — simulated
outcomes vs predicted means, per-draw aggregation, the coverage test, the
mean-parameter trap, and the `bauer`/PyMC APIs that do and do not give you
simulated outcomes — is in the **bayesian-workflow** skill,
`references/ppc_construction.md`. Read that one first if you are the one
computing the band; getting it wrong makes every design decision here moot,
because the band will be a hairline and every model will look broken.

## The one rule that matters

**Observed data is the anchor (points/markers); the model is the overlay (line
+ shaded credible band) — never the reverse.** The eye should land on the data
first and read the model as "how well does this curve+band cover those points."
A PPC where the model is drawn as prominent points and the data as a faint line
has the visual hierarchy backwards and reads as if the simulation were the
measurement.

- **Data**: markers (filled circles), the strongest ink, and **no error bars or
  shaded band** — see "Don't draw the noise twice" below.
- **Model**: posterior-predictive **median** as a line, **95% HDI** as a shaded
  band behind it (`alpha` ~0.2–0.25, no edge), optionally a darker **50% HDI**
  inner band. Same hue as the condition.
- One color per condition, consistent with the rest of the figure (color is
  semantic across panels — see the main skill).

## Don't draw the noise twice

**The observed points get no SEM band, bootstrap band, or error bars.** A
correctly built predictive band already contains the measurement noise: it is
the distribution of datasets like the one collected. The observed summary is a
single realisation to be checked against that distribution — not a second
estimate with its own uncertainty to be reconciled with the first.

Drawing both double-counts the same noise, in the direction that hides misfit:
two overlapping bands nearly always touch somewhere, so a genuine discrepancy
reads as "the intervals overlap, fine". A PPC is a check, and the check is *is
the point inside the band* — ink around the point makes that unanswerable by
eye.

The urge to add SEM bars is itself a symptom: it shows up when the band was
built from predicted means and looks implausibly tight. Fix the band (see
**bayesian-workflow**), don't paper over it with a second one.

## The point of a PPC is to expose misfit, not hide it

A PPC that has been smoothed or aggregated until the model always covers the
data has been robbed of its function. Bin at a resolution that can still *show
a discrepancy*; put the data points where the model is weakest (tails, fastest
RTs, extreme stimulus levels) on the plot, not averaged away. A good PPC panel
earns its place by either building trust (band covers data across the range) or
pointing at the failure (data sits outside the band somewhere specific) —
annotate that failure directly ("Model underpredicts fast errors").

Put the band's **coverage** on the panel — the fraction of observed points
inside the nominal 95% band. It is one number, it is the whole check, and it
stops a reader (or you, six months later) from eyeballing "looks about right".

## Plotting recipe

Data points over model band, direct-labelled, no legend:

```python
for cond, col in palette.items():
    m = model[model.condition == cond].sort_values('x')
    d = data[data.condition == cond].sort_values('x')
    ax.fill_between(m['x'], m['lo'], m['hi'], color=col, alpha=0.22, lw=0, zorder=1)
    ax.plot(m['x'], m['median'], color=col, lw=1.3, zorder=2)
    ax.plot(d['x'], d['observed'], 'o', color=col, ms=4, mec='white', mew=0.5, zorder=3)
    ax.text(d['x'].iloc[-1], d['observed'].iloc[-1], '  ' + cond.capitalize(),
            color=col, va='center')
```

**Plot the spread as well as the central tendency.** A model can match a bias
or accuracy curve exactly and get the response variability badly wrong; in
practice that second panel is where models fail first. Same treatment: observed
SD per bin as markers, simulated SD per bin as line + band.

## The standard PPC panel types

- **Psychometric PPC** (choice vs stimulus): x = stimulus / decision variable
  (binned), y = P(response); data points + model band, one series per
  condition. Chance line at 0.5 (thin gray dashed).
- **Chronometric PPC** (RT vs stimulus): same layout, y = mean or median RT.
  Often paired beneath the psychometric sharing the x-axis.
- **RT distribution PPC**: overlay the observed RT histogram (or KDE) with
  model-simulated RT density; or, better for decision models, a
  **quantile-probability plot** (RT quantiles — .1/.3/.5/.7/.9 — on y, response
  proportion on x, correct vs error). Data quantiles as markers, model
  quantiles as lines/bands. Split correct vs error (errors are where DDMs most
  often misfit).
- **Defective CDFs / cumulative RT** for two-choice RT: cumulative distribution
  per response, scaled by that response's probability.

## Group vs per-subject panels

- **Group PPC**: points are across-subject means — say so in the caption.
- **Per-subject PPC**: a `FacetGrid` with one small panel per subject is the
  honest way to show the model fits *individuals*, not just the grand mean (a
  model can fit the average and miss every subject). Shared axes across panels.
  Expect wide bands — each subject has few trials per bin, and that width is
  the correct predictive uncertainty, not a defect to be smoothed away.

## Caption language

- "Points: observed data (across-subject means). Line and shaded band:
  posterior-predictive median and 95% HDI."
- Say "posterior predictive", and "HDI"/"credible", never "confidence".
- If data are binned, state the binning ("9 quantile bins of the decision
  variable") — a reader cannot otherwise tell signal from binning artifact.

## Anti-patterns

- Model drawn as bold markers, data as a thin line (hierarchy reversed)
- Error bars or a bootstrap band on the observed points
- Plotting the mean of pp draws as a line with **no band**
- Different bins for data vs model (the discrepancy is then partly a binning
  artifact) — use shared bins
- Over-binning until everything fits — a PPC that cannot fail is not a check
- Showing only the central-tendency panel and never the spread
