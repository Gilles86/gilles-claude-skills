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

1. **Despine, then offset the remaining spines.** Top and right always off. Left and bottom kept, but offset outward from the data by a few points (`sns.despine(offset=5, trim=True)`). The "trim" is what makes the spine stop at the data's extent rather than running past it — this small detail is core to the look.
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
- **But when the data IS the only thing on the figure** (no model overlay, no second condition to contrast against), use a clear vivid color, **not gray**. The "data in gray" rule is a *don't-compete* rule for when there's a colored model fit alongside — applied to a data-only figure, it makes the figure read as dull and unfinished. If the talk / paper has an established palette (project illustrations, slide deck), match the panel's color to *what's being measured* (e.g., red for an HP-distractor effect if the illustration uses red for HP, blue for an attention-field effect, etc.). Make the color carry semantic weight.

**Rules that apply across both:**
- Use color to encode an actual variable, not to decorate. If two lines could be distinguished by linestyle (solid vs dashed) or marker shape and the difference is categorical, consider doing that instead and keeping color free for a continuous variable.
- **Color is semantic across the entire figure, not just within a panel.** Once a hue is assigned to a condition in one panel (e.g. blue = cue-left in panel A), the reader will read that same hue as the same condition wherever it appears. If a different panel collapses across that condition (a grand-mean curve, an aggregate bar), do **not** reuse the same hue — switch to a neutral gray. Otherwise the aggregate panel falsely reads as "this is cue-left data". Same logic in reverse: don't introduce a new hue for a condition that already has one in another panel. Color persistence across panels is one of the strongest correctness signals in a paper figure.
- Test by converting the figure to grayscale (`convert -colorspace Gray fig.pdf fig_gray.pdf` or equivalent). If conditions become indistinguishable, the encoding is leaning too hard on hue alone — add linestyle or marker variation.
- Avoid pure red and pure green together (deuteranopia). The hand-picked palette above is safe.

## Error and uncertainty

How uncertainty is drawn is one of the strongest style signals.

- **Continuous predictors (psychometric / tuning curves)**: shaded ±1 SEM bands behind the line, same hue, alpha ~0.2–0.3, no edge. In seaborn this is the default for `lineplot` with `errorbar=('se', 1)`. Confirm the band is drawn behind the line (`zorder`), not on top.
- **Discrete conditions (bar / point plots)**: thin error bars with **no caps** or very short caps (`capsize=0` or `capsize=2`), drawn with `errwidth=0.8`. The capped T-bars from default matplotlib look amateurish at publication size.
- **Central tendency: mean ± SEM is the conference default** (VSS, OHBM, SfN — audience reads error bars as SEM unless told otherwise). Use it by default. But: SEM is only meaningful when the **mean** is meaningful — i.e., when the data isn't dominated by a few extreme outliers. For high-variance / heavy-tailed parameter estimates (e.g., attention-field gains in low-SNR ROIs that occasionally blow up to |g| > 5 or 10), the mean gets pulled off the visible swarm by a couple of subjects and SEM becomes huge. Two honest fixes:
  - **Trim then mean ± SEM** with a fixed absolute or per-ROI cutoff (e.g., `|value| > 4` or "drop subjects more than 3 × IQR from the median"). Annotate `n_kept (−k_dropped)` under each x-tick AND state the trim rule in a small in-figure note (`Mean ± SEM · outliers |g| > 4 excluded`) so the audience doesn't read default-SEM into trimmed-SEM. This is the talk-friendly choice: the audience gets what they expect with a labeled deviation.
  - **Median + bootstrap 95% CI** (or HDI) — robust to outliers and matches the visible swarm exactly. The cost is the audience needs to read the label; without it they'll assume SEM. Only worth it if outliers are a substantive part of the story.
- **Make the central-tendency marker pop above the swarm.** A 13-pt diamond with a *thick dark edge* (1.5–2 pt) on top of translucent subject dots (alpha 0.3–0.4) reads as "this is the summary, those are the data". A 6-pt marker with thin edge and the same color as the dots disappears into the cloud. When SEM is genuinely small (well-estimated effect; SEM ≪ marker radius in data units), shrinking the marker (e.g., 9 pt) lets the bars peek out — don't inflate the bars artificially.
- **Bayesian / posterior intervals**: shaded HDI bands rather than discrete bars whenever the predictor is continuous. See the dedicated section below for working with PyMC / `bauer` posteriors and seaborn's `errorbar` parameter.
- **Bootstrap distributions or single-trial spread**: use stripplot or swarmplot overlaid on point estimates, with low alpha (0.3–0.5) and small markers (size 2–3). Don't use box plots for n < ~20 per condition — show the points.
- **Always state in the caption what the error represents.** "Shaded regions show ±1 SEM across subjects" or "Error bars show 95% bootstrap CI". This is non-negotiable for the audience even if obvious to the author.

## Posteriors from PyMC / bauer

The convention for Bayesian posteriors: **posterior median (or mean) as
the central line, 95% HDI as a shaded band, and 50% HDI as a darker
inner band when the figure can carry it.** Always say "credible
interval" or "HDI" in the caption — never "confidence interval", which
is a different object the audience for this work cares about.

Plotting recipes (`arviz.InferenceData` → long-form DataFrame → seaborn
`lineplot` with HDI errorbars, including the HDI-vs-equal-tailed
distinction for skewed posteriors, the forest-plot pattern for discrete
per-condition posteriors, and caption language) live in
[references/bayesian_posteriors.md](references/bayesian_posteriors.md).

## Axes: the details that matter

- **Tick locations are chosen, not defaulted.** Pick 3–5 ticks per axis. Round numbers, ideally at meaningful values (the lowest and highest stimulus levels, integer log-spaced values, etc.). Use `ax.set_xticks([...])` explicitly.
- **The data extremes belong on the axis.** Matplotlib defaults pick "round" interior ticks (10, 15, 20) and skip the endpoints of the actual data range (5 and 25), which makes the reader infer the range instead of seeing it. Always include the minimum and maximum data values as explicit ticks — for a 5–25 numerosity range, the right ticks are `[5, 10, 15, 20, 25]`, not `[10, 15, 20]`. Same for any psychophysics axis (contrast levels, spatial frequencies, n-back levels): the extreme stimulus values are part of the design and the reader should see them.
- **Align y-axes across panels that show the same quantity.** When a row or column of panels all plot the same thing (Pearson r, proportion, cvR², SD), they need a shared y-scale or the reader cannot compare across panels — they'll mis-read a panel-specific "tall bar" as a real effect when it's just an autoscaled range. `sharey="row"` in `plt.subplots` is the easy fix. *Exception*: a metric on a clearly different scale (e.g., a "delta" or "specificity" row whose values are 5–10× smaller than the matched/cross panels feeding it) gets its own zoomed range — but say so in the row label, and never autoscale silently. Compute the y-limits **after** any aggregation step so they fit the actual rendered data, not pre-aggregated extremes.
- **Don't repeat N across panels if it's the same everywhere.** If every panel uses the same set of subjects, the N=… label belongs in one corner of the first panel (or in the caption), not in all of them. Repeated N labels are noise that distracts from the data — like writing the date on every paragraph of a journal entry.
- **Log axes**: when a variable spans orders of magnitude (contrast, frequency, numerosity), use log scale. Ticks at decadal values with minor ticks at 2, 5 between them. Hide minor tick labels. Consider explicit `ScalarFormatter` to avoid scientific notation when values are 0.01–100.
- **Trim the axis to the data.** `sns.despine(trim=True)` does most of this, but verify — the spine should end at the last tick, not extend past it.
- **Axis labels are short.** "Contrast" not "Stimulus contrast (Michelson)" in the label; put units in parentheses, put the qualifier in the caption. Example: `Contrast (%)`, `Firing rate (spikes/s)`, `Reaction time (s)`, `WTP (CHF)`. See the capitalization rule below.
- **Drop the axis label when the ticks already name what's on the axis.** If the tick labels are categorical names that describe themselves — `["NPCl", "NPCr"]`, `["Mix shared-RF", "Sum", ...]`, `["sub-01", "sub-02", ...]`, `["V1", "V2", "V3"]` — adding an axis label that just summarizes the category type ("ROI", "Model", "Subject", "Area") is redundant. The ticks ARE the label. Stripping the redundant word frees up space and pulls the eye to the data. Default to **omitting categorical axis labels and only add one when the category isn't obvious** (e.g. numeric tick values where the reader genuinely can't tell what the numbers refer to). When in doubt, set the label to `""` and check whether anything was lost — usually nothing was.
- **Y-labels short, statistical noise to the caption.** Long descriptive y-labels — "Mean ± SEM proportion of voxels with highest cvR²" — are the worst offenders. Shorten to the *quantity* being plotted ("Highest-cvR² fraction") and push the central-tendency / error / n information to the caption or a small in-panel note. The reader can see "bar + dots + error bar" and read it as mean ± SEM directly; spelling it out in the y-label is text in service of nothing.
- **The general rule: every piece of text on a figure must add information the data itself doesn't carry.** Apply to axis labels, in-panel annotations, titles, legend titles. Each time you write text, ask "could the reader infer this from the data?" — if yes, cut it.
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

Specializations of the conventions above for the panel types that come
up most — psychometric / tuning curve, time-series / event-locked
average, condition comparison (point/bar), scatter, heatmap — live in
[references/figure_types.md](references/figure_types.md). Load it when
starting a panel of that type; the universal rules in this skill still
apply on top.

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
