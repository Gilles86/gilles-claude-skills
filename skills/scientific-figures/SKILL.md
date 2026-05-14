---
name: scientific-figures
description: Produce publication-quality scientific figures in a restrained, vision-science-inflected house style. Use this skill whenever the user asks for plots, figures, or visualizations for a paper, preprint, talk, or grant — especially for vision, psychophysics, neuroscience, or computational modeling work — and any time the user mentions "publication-quality", "for a paper", "Nature figure", "figure for my manuscript", or similar. Default to this skill for any seaborn/matplotlib plotting task in a scientific context unless the user explicitly asks for a different aesthetic (e.g., ggplot, default matplotlib, plotly dashboard).
---

# Scientific figures, publication-quality

The goal is figures that look like they came out of a careful vision-science house style. Concretely that means: high information density, almost nothing on the page that isn't data or essential reference, restrained palette, sans-serif type, and obsessive attention to a small set of details that distinguishes a real scientific figure from a default `seaborn` call.

The plotting stack is **seaborn on top of matplotlib**. Use seaborn for the statistical layer (categorical structure, faceting, distributional plots) but reach for matplotlib directly whenever the seaborn default doesn't give the control needed — axis spine offsets, custom tick locations, panel letters, direct labeling, in-panel annotations. Don't fight seaborn; just don't be afraid to drop below it.

## The point of a figure

Every figure tells one story, and the **panels alone** carry that story. A reader who sees the figure without the caption — on a slide, in a tweet, skimming a PDF — should understand the main finding. The caption exists for bookkeeping: n, what the error bars represent, statistical tests, abbreviations, panel-by-panel detail. It is not where the message lives.

This is the stronger version of the usual "figure stands alone" rule, and it's the one that actually distinguishes good figures from merely correct ones. If understanding the figure requires reading the caption, the figure isn't done — and the fix is almost always in-panel annotations (see below) that name the effect, the model, the reference, or the comparison directly on the data.

If the story can't be summarized in one sentence ("we measured X and found Y"), the figure isn't done either. If a panel doesn't contribute to that story, cut it. If two panels make the same point, merge them.

Every choice below — spine offsets, color, error bands, panel order, annotations — serves this. Composition is editing.

## Physical size: pick it first, everything follows

Before any plotting, decide the final rendered size in centimetres or inches. Font sizes, line weights, marker sizes, panel proportions — all of these only make sense relative to the physical size of the figure on paper or screen. A figure designed for a 3.5" journal column and pasted onto a 16:9 slide will have unreadable axis labels; a figure designed for a poster and shrunk into a paper will have laughably thick lines.

Concrete defaults by medium:

| Medium                          | Width                  | Notes                                                                           |
| ------------------------------- | ---------------------- | ------------------------------------------------------------------------------- |
| Journal, single column          | 3.5" / 89 mm           | Most Nature, Science, eLife, J Neurosci single-column figures.                  |
| Journal, 1.5 column             | 5" / 127 mm            | Intermediate width when a single column is too cramped for multi-panel layouts. |
| Journal, double column / full   | 7.25" / 184 mm         | Multi-panel main figures spanning the page.                                     |
| Talk slide (16:9, 1920×1080)    | 10–13" effective       | Bigger fonts (14–18 pt). Don't reuse paper figures — regenerate at slide size.  |
| Poster panel                    | 8–16" depending on n   | Bigger fonts (16–24 pt) and thicker lines (1.5–2.5 pt). Same rules otherwise.   |
| Grant proposal figure           | usually 6.5" full width | Read at print size; treat like a journal figure.                                |

Height is set by content, but as a starting point: single panels are roughly 1:1 to 4:3 (width:height), time series wider (2:1 or 3:1), multi-panel figures whatever the grid demands.

Set the size at figure creation, never at export:

```python
fig, axes = plt.subplots(1, 3, figsize=(7.25, 2.5), constrained_layout=True)
```

When the target medium changes, **regenerate** the figure at the new physical size with the same code. Don't `\includegraphics[width=0.5\textwidth]` a figure designed for full-column width — that scales the fonts down with the figure and breaks the carefully-chosen size hierarchy. The rule is: one figure, one physical size, one rendered file.

If the user hasn't specified a target medium, ask — it's the single decision that affects the most downstream choices.

## The non-negotiables

These are the things that most reliably separate a real scientific figure from a generic seaborn plot. If only a few things are done from this whole document, do these:

1. **Despine, then offset the remaining spines.** Top and right always off. Left and bottom kept, but offset outward from the data by a few points (`sns.despine(offset=5, trim=True)`). The "trim" is what makes the spine stop at the data's extent rather than running past it — this is a Cleveland/Tufte move and is core to the look.
2. **Ticks point outward, short, thin.** Never inward, never long. `plt.rcParams['xtick.direction'] = 'out'` and `'ytick.direction' = 'out'`, with `xtick.major.size: 3` and `xtick.major.width: 0.8`.
3. **Helvetica throughout, generous sizes — ~8 pt tick labels, ~9–10 pt axis labels, ~9–10 pt annotations.** Helvetica is the house font here — not "a sans-serif", not Arial as a substitute. If Helvetica isn't installed, install it or use a metric-compatible alternative (Helvetica Neue, TeX Gyre Heros); only fall back to Arial as a last resort and flag the substitution to the user. Never use the platform default. Err on the side of *larger* text — a figure where the labels are comfortably readable at print size looks confident; one where they're squeezed to the minimum looks cramped. No serifs anywhere.
4. **Direct-label conditions; avoid legends.** A legend is a key the reader has to consult — it pulls the eye off the data and reintroduces the caption-dependence the figure is trying to avoid. Place condition labels directly on the data, at the right endpoint of the line or next to the relevant cluster of points, in the same color as the data they label. Use `ax.text` or `ax.annotate` for this. If a legend is genuinely unavoidable (e.g., too many conditions for direct labels to fit), use `frameon=False` and place it where it doesn't compete with data.
5. **Figure size in physical units, set first, never changed by export.** Font sizes in points only mean something relative to the *rendered* size of the figure on paper. A 10pt label on a 3.5" wide figure looks right; the same 10pt label on a figure matplotlib auto-sized to 6.4" looks small, and on a 12" poster panel it looks tiny. So: pick the physical size first — single column ≈ 3.5" (88 mm), 1.5-column ≈ 5" (127 mm), double column ≈ 7.25" (180 mm), poster panels typically 8–16" wide depending on the poster — then set everything else in proportion. Use `figsize=(w, h)` in inches at figure creation; never resize the PDF afterwards in Illustrator or LaTeX (`\includegraphics[width=...]`) — that rescales the fonts and breaks the entire size hierarchy. If the figure needs to fit a different width, regenerate it at that width.
6. **Vector output, fonts as text.** Save as PDF or SVG with `rcParams['pdf.fonttype'] = 42` and `rcParams['ps.fonttype'] = 42` so fonts remain editable in Illustrator rather than being converted to paths.

If a figure has all six of these and nothing else from this document, it will still look broadly correct. The rest of the document is about getting from "broadly correct" to "actually good".

## Preferred seaborn functions

Not all seaborn functions sit equally well in this aesthetic. Reach for these:

- **`sns.FacetGrid`** — the preferred way to build any multi-panel figure where panels share a common structure (e.g., one panel per subject, per condition, per ROI, per model). FacetGrid composes cleanly with the rcParams above, gives consistent axes across panels for free, and the `.map_dataframe()` pattern keeps plotting code declarative. Default to FacetGrid for repeated-structure figures rather than building a `plt.subplots` grid by hand.
- **`sns.relplot` / `sns.catplot` / `sns.displot`** — the figure-level wrappers around FacetGrid. Use these for quick multi-panel figures; drop to `FacetGrid` + `.map_dataframe()` when you need a custom plotting function per panel.
- **`sns.lineplot`** — for continuous predictors with shaded error bands. Pass `errorbar=('se', 1)` for ±1 SEM; the default 95% bootstrap CI is usually too wide for the within-subject case.
- **`sns.pointplot`** — for discrete conditions. Almost always preferable to `barplot` at publication size: thin errorbars (no caps), small markers, lighter ink.
- **`sns.stripplot`** / **`sns.swarmplot`** — overlay individual data points on a pointplot when n is small enough to show them (≤ 30 per condition).
- **`sns.regplot`** — only when the regression line is genuinely the message. Otherwise plot the scatter with `ax.scatter` and add the line manually so you control its appearance.

Avoid by default:

- **`sns.barplot`** with no individual points overlaid — wastes ink, hides the n
- **`sns.boxplot`** for small n — show the points
- **`sns.violinplot`** — kernel-smoothing artifacts can mislead; if the distribution matters, show points or a histogram
- **`sns.heatmap`** with annotations inside cells — fine for very small matrices, but for anything larger drop to `ax.imshow` and add a colorbar manually for tighter control

### A note on FacetGrid and the despine offset

The `offset` and `trim` arguments to `sns.despine()` don't propagate cleanly through `FacetGrid`'s built-in despining. The pattern that works:

```python
g = sns.FacetGrid(df, col='condition', height=2.2, aspect=1.0, despine=False)
g.map_dataframe(sns.lineplot, x='contrast', y='response', errorbar=('se', 1))
g.set_titles('{col_name}')  # short panel titles, capitalized first letter
sns.despine(fig=g.figure, offset=5, trim=True)
```

Pass `despine=False` to FacetGrid, then call `sns.despine` on the figure afterwards. Otherwise the offset is ignored on some axes.

## Recommended rcParams block

Drop this at the top of any figure-generating script. It encodes most of the non-negotiables and a few additional refinements. Adjust font sizes upward for talks and posters (see the physical-size section above).

```python
import matplotlib as mpl
import seaborn as sns

mpl.rcParams.update({
    # Typography — Helvetica is the house font, not a fallback
    'font.family': 'Helvetica',
    'font.sans-serif': ['Helvetica', 'Helvetica Neue', 'TeX Gyre Heros', 'Arial'],
    'font.size': 9,
    'axes.labelsize': 10,
    'axes.titlesize': 10,
    'xtick.labelsize': 8,
    'ytick.labelsize': 8,
    'legend.fontsize': 8,
    'mathtext.fontset': 'stixsans',  # if mathtext is used at all, keep it sans-serif

    # Axes
    'axes.linewidth': 0.8,
    'axes.spines.top': False,
    'axes.spines.right': False,
    'axes.labelpad': 4,

    # Ticks: outward, short, thin
    'xtick.direction': 'out',
    'ytick.direction': 'out',
    'xtick.major.size': 3,
    'ytick.major.size': 3,
    'xtick.minor.size': 1.5,
    'ytick.minor.size': 1.5,
    'xtick.major.width': 0.8,
    'ytick.major.width': 0.8,

    # Lines and markers
    'lines.linewidth': 1.2,
    'lines.markersize': 4,
    'patch.linewidth': 0.5,

    # Legend
    'legend.frameon': False,
    'legend.handlelength': 1.5,

    # Output: editable text in vector formats
    'pdf.fonttype': 42,
    'ps.fonttype': 42,
    'svg.fonttype': 'none',

    # Figure
    'figure.dpi': 150,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.02,
})

sns.set_context('paper')  # don't use 'notebook' or 'talk' for paper figures
```

After plotting, always finish with `sns.despine(offset=5, trim=True)`. If using `FacetGrid` or `catplot`, pass `despine=False` initially and call `sns.despine(offset=5, trim=True)` afterwards — the offset/trim combination doesn't get applied correctly through the high-level seaborn wrappers.

## Color

Default seaborn and matplotlib palettes (`tab10`, `deep`, `Set1`) are a tell that nobody chose the colors. Don't use them. A good scientific figure either uses one of a small set of perceptually-uniform palettes for ordered/continuous variables, or a hand-picked muted categorical palette of 2–5 colors for discrete conditions.

**For continuous / ordered conditions** (e.g., contrast levels, eccentricities, time points, magnitude bins, model layers):
- `viridis`, `cividis`, `mako`, `rocket` — all perceptually uniform, print-safe, colorblind-friendly
- Truncate the extremes when the endpoints get too dark or too bright for points/lines on a white background: `sns.color_palette('mako', as_cmap=True)(np.linspace(0.15, 0.85, n))`
- For divergent quantities (e.g., signed contrast, attention modulation around baseline), use `vlag`, `coolwarm`, or `RdBu_r` centered at zero

**For categorical conditions** (typically 2–5 conditions):
- `sns.color_palette('colorblind')` is acceptable but slightly oversaturated; prefer muted variants
- Hand-picked palettes look more deliberate. A reliable starting point is desaturated versions of red, blue, and a neutral gray/green:
  ```python
  palette = ['#3B5BA5', '#C44E52', '#5D8C3F', '#8172B2', '#9C9C9C']  # blue, red, green, purple, gray
  # or, for two-condition contrasts, often just blue vs gray:
  palette = ['#3B5BA5', '#7F7F7F']
  ```
- For a "model vs data" contrast, a common idiom is **data in black/dark gray points, model fit as a colored line**. Don't compete: let the data be the visual anchor.

**Rules that apply across both:**
- Use color to encode an actual variable, not to decorate. If two lines could be distinguished by linestyle (solid vs dashed) or marker shape and the difference is categorical, consider doing that instead and keeping color free for a continuous variable.
- Test by converting the figure to grayscale (`convert -colorspace Gray fig.pdf fig_gray.pdf` or equivalent). If conditions become indistinguishable, the encoding is leaning too hard on hue alone — add linestyle or marker variation.
- Avoid pure red and pure green together (deuteranopia). The hand-picked palette above is safe.

## Error and uncertainty

How uncertainty is drawn is one of the strongest style signals.

- **Continuous predictors (psychometric / tuning curves)**: shaded ±1 SEM bands behind the line, same hue, alpha ~0.2–0.3, no edge. In seaborn this is the default for `lineplot` with `errorbar=('se', 1)`. Confirm the band is drawn behind the line (`zorder`), not on top.
- **Discrete conditions (bar / point plots)**: thin error bars with **no caps** or very short caps (`capsize=0` or `capsize=2`), drawn with `errwidth=0.8`. The capped T-bars from default matplotlib look amateurish at publication size.
- **Bayesian / posterior intervals**: shaded HDI bands rather than discrete bars whenever the predictor is continuous. See the dedicated section below for working with PyMC / `bauer` posteriors and seaborn's `errorbar` parameter.
- **Bootstrap distributions or single-trial spread**: use stripplot or swarmplot overlaid on point estimates, with low alpha (0.3–0.5) and small markers (size 2–3). Don't use box plots for n < ~20 per condition — show the points.
- **Always state in the caption what the error represents.** "Shaded regions show ±1 SEM across subjects" or "Error bars show 95% bootstrap CI". This is non-negotiable for the audience even if obvious to the author.

## Posteriors from PyMC / bauer: credible intervals

Bayesian posteriors are first-class in this tradition — `bauer`, PyMC, NumPyro, Stan all produce posterior samples that need to be plotted as central tendency plus a credible interval. The convention is: **posterior median (or mean) as the central line, 95% HDI as a shaded band, and 50% HDI as a darker inner band when the figure can carry it.** Always say "credible interval" or "HDI", never "confidence interval", in the caption — these are different objects and the audience for this work cares.

A practical aside: **HDI ≠ equal-tailed interval** for skewed posteriors. The highest-density interval is the shortest interval containing the specified probability mass; the equal-tailed interval is the 2.5%–97.5% quantile range. They coincide for symmetric posteriors but diverge for skewed ones (variance components, bounded parameters, log-scale parameters). For `bauer` hierarchical posteriors, prefer HDI by default — it's the more honest summary when distributions are skewed.

### Plotting posterior samples with seaborn

Seaborn 0.12+ added an `errorbar` parameter that accepts either a built-in method name or a custom callable. Both options are useful:

**Option 1 — equal-tailed (percentile) intervals via the built-in `"pi"`.** Simplest if equal-tailed is acceptable. Works directly when posterior samples are in long form (one row per draw × x-value):

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

**Option 2 — true HDI via a custom callable using ArviZ.** The right choice for skewed posteriors:

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

For nested HDI bands (50% + 95%), call `lineplot` twice on the same axes — once with `hdi_50`, once with `hdi_95` — and use a slightly darker alpha for the inner band. Plot 95% first so it sits behind 50%.

### Going from an InferenceData object to a long-form DataFrame

`bauer` returns `arviz.InferenceData`. Seaborn wants long form. The conversion idiom:

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

For posterior *predictive* draws over a fine x-grid (e.g., a smooth psychometric curve with credible bands), generate predictions at, say, 200 x-values inside the model and run the same conversion. Seaborn will aggregate over the `sample` index automatically when you map `x` and `y='mu'`.

### Discrete posteriors (per-condition parameter posteriors)

When the posterior is over discrete conditions (e.g., per-subject parameter estimates), the equivalent of the lineplot-with-HDI is a pointplot or custom forest plot. Two patterns:

- **Pointplot with HDI errorbars**: `sns.pointplot(data=df_post, x='condition', y='theta', estimator='median', errorbar=hdi_95)`. Works well when conditions are few and the message is about means.
- **Forest plot** (one row per subject/condition, horizontal HDI segments): drop to matplotlib. `ax.hlines(y=subject_ids, xmin=hdi_low, xmax=hdi_high, lw=1.5)` for the 95% segment, then a thicker overlay for the 50%, then a marker at the median. ArviZ has `az.plot_forest()` but its defaults don't match this style; either restyle it heavily with the rcParams above or build the forest plot manually for fine control.

### Caption language for posteriors

State the error metric precisely:
- "Shaded bands show 95% highest-density credible intervals over posterior samples."
- "Error bars show 95% HDI; points are posterior medians."
- "Inner and outer bands show 50% and 95% HDI."

Don't write "95% CI" without qualification — readers will read it as confidence interval. Either spell out "credible interval" or use "HDI".

## Axes: the details that matter

- **Tick locations are chosen, not defaulted.** Pick 3–5 ticks per axis. Round numbers, ideally at meaningful values (the lowest and highest stimulus levels, integer log-spaced values, etc.). Use `ax.set_xticks([...])` explicitly.
- **Log axes**: when a variable spans orders of magnitude (contrast, frequency, numerosity), use log scale. Ticks at decadal values with minor ticks at 2, 5 between them. Hide minor tick labels. Consider explicit `ScalarFormatter` to avoid scientific notation when values are 0.01–100.
- **Trim the axis to the data.** `sns.despine(trim=True)` does most of this, but verify — the spine should end at the last tick, not extend past it.
- **Axis labels are short.** "Contrast" not "Stimulus contrast (Michelson)" in the label; put units in parentheses, put the qualifier in the caption. Example: `Contrast (%)`, `Firing rate (spikes/s)`, `Reaction time (s)`, `WTP (CHF)`. See the capitalization rule below.
- **Math in labels: use Unicode, not mathtext, when possible.** Matplotlib's `$...$` mathtext renders in Computer Modern by default and breaks the Helvetica consistency. For Greek letters, subscripts, simple operators, just put Unicode directly in the string: `"σ (deg)"`, `"Δ contrast"`, `"log₂(numerosity)"`, `"R²"`. Save mathtext for genuinely structural math (fractions, integrals, summations), and when you do need it, set `rcParams['mathtext.fontset'] = 'stixsans'` so the math stays sans-serif, or use `usetex=True` with a Helvetica preamble if the project uses LaTeX.
- **No grid lines.** None. If a reference value matters, draw it explicitly as a thin gray dashed `axhline` or `axvline` with `color='0.7'`, `lw=0.6`, `ls='--'`, `zorder=0`.

## Capitalization: first letter always

Every piece of text on a figure starts with a capital letter — axis labels, annotations, legend entries, panel titles, condition labels. Even two-word annotations: "Model fit", not "model fit". "Stimulus onset", not "stimulus onset". The rest of the phrase is lowercase unless it's a proper noun, acronym, or unit symbol (`Hz`, `CHF`, `RT`).

This is small but it's one of the strongest readability signals — figures where some labels start lowercase and others don't look unfinished, and the lowercase-everywhere style (common in defaults) reads as informal. Consistency here is free; just do it everywhere.

## In-panel annotations: guide the reader

In-panel annotations are how the figure carries its message without the caption. Don't make the reader hunt for the effect — point at it. The house style is short text labels with a thin curved arrow connecting the label to the relevant data feature. "Attention shifts the peak", "Model fit", "Stimulus onset", "Chance", "Inflection point". Two or three words. The figure becomes self-narrating: a reader skimming only the panels, with no caption visible, should extract the core finding from the annotations alone.

Use `ax.annotate` for this — it gives you the arrow plus text positioning in one call:

```python
ax.annotate(
    'Attention shifts peak',
    xy=(peak_x, peak_y),               # the data point being pointed at
    xytext=(peak_x + 0.5, peak_y + 0.3),  # where the text sits
    fontsize=7,
    ha='left', va='center',
    arrowprops=dict(
        arrowstyle='-',                 # plain line, no arrowhead; or '->' for a small head
        connectionstyle='arc3,rad=0.2', # gentle curve — flat lines look stiff
        color='0.3',
        lw=0.6,
    ),
)
```

A few rules:
- **Curved, not straight.** `connectionstyle='arc3,rad=0.2'` gives the gentle hand-drawn-looking arc that's a signature of the style. Adjust `rad` (typically 0.1–0.3, signed) so the arrow doesn't cross data.
- **Thin and gray, not black.** `color='0.3'` or `'0.4'`, `lw=0.6`. The annotation should support the data, not compete with it.
- **No arrowhead, or a very small one.** A plain line (`arrowstyle='-'`) often reads cleaner than `'->'`. Reserve arrowheads for cases where the direction of pointing is genuinely ambiguous.
- **Short text, capitalized first letter, no terminal punctuation.** "Model fit", not "model fit" or "Best-fitting model prediction." If it needs more than four or five words, it belongs in the caption.
- **Place text where it doesn't overlap data.** Whitespace in the upper-right or lower-left of the panel is usually available. If the panel is dense, consider a leader line out into the margin.
- **One to three annotations per panel, maximum.** More than that and you've stopped guiding and started cluttering.

Use annotations to label: the key effect ("Peak shift", "Saturating nonlinearity"), the model ("Efficient-coding fit"), reference values ("Chance", "Veridical"), and event markers in time series ("Stimulus onset", "Response"). Don't use them to repeat what the axis label already says.

## Multi-panel layout

Real papers have multi-panel figures. Default to `plt.subplots` for simple grids and `matplotlib.gridspec` when panels have different sizes or share complex relationships.

- **Panel letters: A, B, C, D, …** in bold sans-serif, slightly larger than the axis labels (10–12 pt), placed at the top-left **outside** the axes. Use `ax.text(-0.15, 1.05, 'A', transform=ax.transAxes, fontsize=12, fontweight='bold', va='bottom', ha='right')`. Same letter position across all panels — pick coordinates that work, then reuse.
- **Don't waste space.** `plt.tight_layout()` is a reasonable start; `constrained_layout=True` at figure creation is better. If panels share an x or y axis, use `sharex=True` / `sharey=True` and remove redundant tick labels.
- **Align axes across panels.** When two panels show the same quantity (e.g., both show firing rate), they should have the same y-axis range and the same y-axis label position. Eyes should not have to recompute scale across panels.
- **Aspect ratio per panel.** Most data panels look right between 1:1 and 4:3 (width:height). Time-series panels can be wider (2:1 or 3:1). Avoid tall-thin panels unless plotting something genuinely vertical (population stack, anatomical depth).

## Figure-type cheat sheet

The conventions above are generic. Here's how they specialize for the figure types that come up most.

**Psychometric / tuning curve panel:**
- Data points: black or dark gray, size proportional to n if n varies across stimulus levels (`s=n*scale`), error bars (vertical only, no caps, lw=0.8)
- Fit: colored line (one color per subject or condition), 1–1.5 pt, smooth (evaluate at 200+ x-values)
- X-axis often log-scale (contrast, frequency, numerosity)
- Y-axis: probability (0 to 1) or proportion (0 to 1), with ticks at 0, 0.5, 1
- Reference lines: `axhline(0.5)` for chance in 2AFC, thin gray dashed

**Time series / event-locked average (PSTH, BOLD timecourse, pupil trace):**
- Mean as a line, ±SEM as a shaded band of the same hue
- Vertical reference lines at event onsets (`axvline`, thin gray, dashed if not a hard event)
- X-axis label includes the lock event: "Time from stimulus onset (s)"
- For multiple conditions, all on the same axes with direct labels at line endpoints, not a legend

**Comparison of conditions (bar / point plot):**
- Prefer pointplot or stripplot+pointplot over bar plot when n is small (< ~30)
- If using bar: thin (`width=0.6`), unfilled or light fill with darker edge, error bars uncapped
- Always show individual data points as a swarm or strip overlay when subjects ≤ 30 — readers want to see the n and the spread
- Connect within-subject points with thin gray lines (`lw=0.5`, `alpha=0.4`) in repeated-measures designs

**Scatter (correlation, model vs data, individual-difference):**
- Filled circles, single color, size 15–25, edgecolor white or none, alpha 0.6–0.8 if many points
- Identity line (`x = y`) as thin gray dashed when comparing two measurements of the same quantity
- Regression line only if statistically meaningful; report r/r² in the panel as a small text annotation, not in a legend
- Equal aspect ratio (`ax.set_aspect('equal')`) when both axes are the same quantity

**Heatmap (RDM, similarity matrix, model coefficients):**
- `vlag` or `RdBu_r` for divergent, `mako` or `viridis` for unsigned
- Square cells, no internal gridlines, no annotations inside cells unless n × n is small (< 8)
- Colorbar: thin (`shrink=0.6`), outside the plot area, with a short label
- For RDMs specifically: symmetric, square aspect, hide the upper triangle if redundant

## Saving the figure

```python
fig.savefig('figure_1.pdf', dpi=300, bbox_inches='tight', pad_inches=0.02)
fig.savefig('figure_1.svg')  # for Illustrator
```

Save both PDF (for direct submission) and SVG (for post-processing). Never save the final figure as PNG for a paper unless explicitly required.

Check the output: open in a PDF viewer at 100% zoom and make sure (1) text is selectable (font is embedded as text, not paths), (2) lines are crisp at the target print size, (3) nothing is clipped at the edges.

## What to ask the user before plotting

Before generating a figure from scratch, briefly confirm:
- **Target medium**: paper (which journal/column width?), talk, poster, preprint? This sets the figure size.
- **Number of panels** and what each shows.
- **The variables**: what's on x, what's on y, what's encoded by color/style, what's faceted?
- **What the error/uncertainty represents** — across-subject SEM, within-subject CI, bootstrap, posterior?

If the user just hands over a dataframe and says "plot it", make reasonable defaults using the principles above and state the assumptions in the response so they can correct course.

## Anti-patterns to avoid

These come up constantly and are worth refusing by default:

- Default `tab10` / `Set1` / `Set2` palettes
- Top and right spines still present
- Inward ticks (this is the matplotlib default and looks wrong)
- Legend with a frame, especially inside the plot area on top of data
- Title on the axes (`ax.set_title`) for paper figures — titling belongs in the caption, not the figure. Talks and posters are different.
- Grid lines as background decoration
- 3D plots, pie charts, dual y-axes — essentially never appropriate for vision-science papers
- PNG output for the final figure
- Bar plots with n < 10 per condition and no individual points shown
- Using the same color hue at different saturations to encode unrelated categorical variables
- Capped error bars at small print size (the caps add noise, not information)

## Final pass: does this figure work?

Before saving and presenting the figure, step back and verify:

1. **Can I state the figure's point in one sentence?** If not, the figure doesn't have a story yet — go back and decide what it's trying to say before polishing further.
2. **Does the panel order match the argument?** A reads first, then B, then C. The eye should travel through the science in the order the argument is made.
3. **Cover the caption. Does the figure still convey the main finding?** This is the hard test. If covering the caption breaks comprehension of the *finding* (not the bookkeeping — n, error metric, statistical test are fine to put in the caption), the figure needs more in-panel annotation. Add a label pointing at the effect, name the model fit, mark the reference value. The panels must carry the message.
4. **Does the caption carry the bookkeeping?** Define every abbreviation, state every error metric, give n, name the statistical test. The caption isn't where the message lives, but it is where readers find the details they need to trust the message.
5. **Is there anything on the figure that isn't data or essential reference?** If yes, remove it.

A figure that passes these five checks is done. Spines, palettes, and tick marks are how the figure earns the right to be looked at — but they don't make the figure say anything.

## When to deviate

Style serves communication, not the other way around. Deviate when:
- The data genuinely requires a non-standard encoding (e.g., circular variables → polar plot, even though polar plots are rare in this tradition)
- The journal has a specific style guide that conflicts — follow the journal
- A talk audience won't read 7pt labels — scale up via `sns.set_context('talk')` rather than fighting the rcParams

Document the deviation briefly in a code comment so the next person (or future you) understands why.
