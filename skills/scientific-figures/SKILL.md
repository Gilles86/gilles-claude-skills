---
name: scientific-figures
description: Produce publication-quality scientific figures in a restrained, vision-science-inflected house style. Use this skill whenever the user asks for plots, figures, or visualizations for a paper, preprint, talk, or grant — especially for vision, psychophysics, neuroscience, or computational modeling work — and any time the user mentions "publication-quality", "for a paper", "Nature figure", "figure for my manuscript", or similar. Default to this skill for any seaborn/matplotlib plotting task in a scientific context unless the user explicitly asks for a different aesthetic (e.g., ggplot, default matplotlib, plotly dashboard).
---

# Scientific figures, publication-quality

The goal: figures in a careful vision-science house style — high information density, almost nothing on the page that isn't data or essential reference, restrained palette, sans-serif type, and obsessive attention to the small details that distinguish a real scientific figure from a default `seaborn` call.

The stack is **seaborn on top of matplotlib**. Use seaborn for the statistical layer (categorical structure, faceting, distributional plots); drop to matplotlib whenever the seaborn default doesn't give the control needed — spine offsets, custom tick locations, panel letters, direct labeling, in-panel annotations. Don't fight seaborn, but don't be afraid to drop below it.

## The point of a figure

Every figure tells one story, and the **panels alone** carry it. A reader who sees the figure without the caption — on a slide, in a tweet, skimming a PDF — should understand the main finding. The caption is for bookkeeping only: n, what the error bars represent, statistical tests, abbreviations, panel-by-panel detail. It is not where the message lives.

This is the stronger version of "figure stands alone", and the one that distinguishes good figures from merely correct ones. If understanding the figure requires the caption, it isn't done — and the fix is almost always in-panel annotations (see below) naming the effect, model, reference, or comparison directly on the data.

If the story can't be summarized in one sentence ("we measured X and found Y"), the figure isn't done either. If a panel doesn't contribute, cut it. If two panels make the same point, merge them. Every choice below — spine offsets, color, error bands, panel order, annotations — serves this. Composition is editing.

## Physical size: pick it first, everything follows

Before any plotting, decide the final rendered size in cm or inches. Font sizes, line weights, marker sizes, panel proportions only make sense relative to the figure's physical size on paper or screen. A figure designed for a 3.5" column and pasted onto a 16:9 slide has unreadable labels; one designed for a poster and shrunk into a paper has laughably thick lines.

Concrete defaults by medium:

| Medium                          | Width                  | Notes                                                                           |
| ------------------------------- | ---------------------- | ------------------------------------------------------------------------------- |
| Journal, single column          | 3.5" / 89 mm           | Most Nature, Science, eLife, J Neurosci single-column figures.                  |
| Journal, 1.5 column             | 5" / 127 mm            | Intermediate width when a single column is too cramped for multi-panel layouts. |
| Journal, double column / full   | 7.25" / 184 mm         | Multi-panel main figures spanning the page.                                     |
| Talk slide (16:9, 1920×1080)    | 10–13" effective       | Bigger fonts (14–18 pt). Don't reuse paper figures — regenerate at slide size.  |
| Poster panel                    | 8–16" depending on n   | Bigger fonts (16–24 pt) and thicker lines (1.5–2.5 pt). Same rules otherwise.   |
| Grant proposal figure           | usually 6.5" full width | Read at print size; treat like a journal figure.                                |

Height is set by content; as a starting point, single panels are roughly 1:1 to 4:3 (width:height), time series wider (2:1 or 3:1), multi-panel whatever the grid demands.

Set the size at figure creation, never at export:

```python
fig, axes = plt.subplots(1, 3, figsize=(7.25, 2.5), constrained_layout=True)
```

When the target medium changes, **regenerate** at the new physical size with the same code. Don't `\includegraphics[width=0.5\textwidth]` a figure designed for full-column width — that scales the fonts down and breaks the size hierarchy. The rule: one figure, one physical size, one rendered file.

If the user hasn't specified a target medium, ask — it's the single decision that affects the most downstream choices.

## The non-negotiables

The things that most reliably separate a real scientific figure from a generic seaborn plot. If you do only a few things from this document, do these:

1. **Despine, then offset the remaining spines.** Top and right always off. Left and bottom kept but offset outward from the data by a few points (`sns.despine(offset=5, trim=True)`). The "trim" makes the spine stop at the data's extent rather than running past it — core to the look.
2. **Ticks point outward, short, thin.** Never inward, never long. `xtick.direction: 'out'`, `ytick.direction: 'out'`, `xtick.major.size: 3`, `xtick.major.width: 0.8`.
3. **Helvetica throughout, generous sizes — ~8 pt tick labels, ~9–10 pt axis labels, ~9–10 pt annotations.** Helvetica specifically — not "a sans-serif", not Arial as a substitute. If it isn't installed, install it or use a metric-compatible alternative (Helvetica Neue, TeX Gyre Heros); fall back to Arial only as a last resort and flag the substitution. Never the platform default. Err *larger* — comfortably readable labels look confident, minimum-squeezed labels look cramped. No serifs anywhere.
4. **Direct-label conditions; avoid legends.** A legend is a key the reader must consult — it pulls the eye off the data and reintroduces caption-dependence. Place condition labels directly on the data, at the line's right endpoint or next to the relevant cluster, in the data's color. Use `ax.text` or `ax.annotate`. If a legend is unavoidable (too many conditions to direct-label), use `frameon=False` and keep it off the data.
5. **Figure size in physical units, set first, never changed by export.** Points only mean something relative to the *rendered* size: a 10 pt label looks right at 3.5" wide, small at an auto-sized 6.4", tiny on a 12" poster panel. Pick the physical size first — single column ≈ 3.5" (88 mm), 1.5-column ≈ 5" (127 mm), double column ≈ 7.25" (180 mm), poster panels 8–16" — then proportion everything to it via `figsize=(w, h)`. Never resize the PDF afterwards (`\includegraphics[width=...]`); regenerate at the new width instead.
6. **Vector output, fonts as text.** Save PDF or SVG with `rcParams['pdf.fonttype'] = 42` and `rcParams['ps.fonttype'] = 42` so fonts stay editable in Illustrator rather than converted to paths.

A figure with all six and nothing else will still look broadly correct. The rest of the document gets from "broadly correct" to "actually good".

## Preferred seaborn functions

Not all seaborn functions sit equally well in this aesthetic. Reach for these:

- **`sns.FacetGrid`** — preferred for any multi-panel figure where panels share a common structure (one per subject, condition, ROI, model). Composes cleanly with the rcParams above, gives consistent axes for free, and `.map_dataframe()` keeps code declarative. Default to it for repeated-structure figures rather than hand-building a `plt.subplots` grid.
- **`sns.relplot` / `sns.catplot` / `sns.displot`** — figure-level wrappers around FacetGrid. Use for quick multi-panel figures; drop to `FacetGrid` + `.map_dataframe()` when you need a custom per-panel plotting function.
- **`sns.lineplot`** — continuous predictors with shaded error bands. Pass `errorbar=('se', 1)` for ±1 SEM; the default 95% bootstrap CI is usually too wide for the within-subject case.
- **`sns.pointplot`** — discrete conditions. Almost always preferable to `barplot` at publication size: thin errorbars (no caps), small markers, lighter ink.
- **`sns.stripplot`** / **`sns.swarmplot`** — overlay individual points on a pointplot when n is small enough (≤ 30 per condition).
- **`sns.regplot`** — only when the regression line is genuinely the message. Otherwise plot the scatter with `ax.scatter` and add the line manually for control.

Avoid by default:

- **`sns.barplot`** with no individual points overlaid — wastes ink, hides the n
- **`sns.boxplot`** for small n — show the points
- **`sns.violinplot`** — kernel-smoothing artifacts can mislead; if the distribution matters, show points or a histogram
- **`sns.heatmap`** with annotations inside cells — fine for very small matrices, but for anything larger drop to `ax.imshow` and add a colorbar manually for tighter control

### A note on FacetGrid and the despine offset

`sns.despine()`'s `offset`/`trim` don't propagate cleanly through `FacetGrid`'s built-in despining. Pass `despine=False` to FacetGrid, then call `sns.despine` on the figure afterwards, or the offset is ignored on some axes:

```python
g = sns.FacetGrid(df, col='condition', height=2.2, aspect=1.0, despine=False)
g.map_dataframe(sns.lineplot, x='contrast', y='response', errorbar=('se', 1))
g.set_titles('{col_name}')  # short panel titles, capitalized first letter
sns.despine(fig=g.figure, offset=5, trim=True)
```

## Recommended rcParams block

Drop this at the top of any figure-generating script. It encodes most of the non-negotiables plus a few refinements. Adjust font sizes upward for talks and posters (see physical-size section).

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

After plotting, always finish with `sns.despine(offset=5, trim=True)`. With `FacetGrid`/`catplot`, pass `despine=False` initially and call it afterwards — offset/trim don't apply correctly through the high-level wrappers.

## Color

Default seaborn/matplotlib palettes (`tab10`, `deep`, `Set1`) are a tell that nobody chose the colors. Don't use them. Use either a perceptually-uniform palette for ordered/continuous variables, or a hand-picked muted palette of 2–5 colors for discrete conditions.

**For continuous / ordered conditions** (contrast levels, eccentricities, time points, magnitude bins, model layers):
- `viridis`, `cividis`, `mako`, `rocket` — perceptually uniform, print-safe, colorblind-friendly
- Truncate the extremes when endpoints get too dark/bright for points/lines on white: `sns.color_palette('mako', as_cmap=True)(np.linspace(0.15, 0.85, n))`
- For divergent quantities (signed contrast, modulation around baseline), use `vlag`, `coolwarm`, or `RdBu_r` centered at zero

**For categorical conditions** (typically 2–5):
- `sns.color_palette('colorblind')` is acceptable but slightly oversaturated; prefer muted variants
- Hand-picked palettes look more deliberate. A reliable start is desaturated red, blue, neutral gray/green:
  ```python
  palette = ['#3B5BA5', '#C44E52', '#5D8C3F', '#8172B2', '#9C9C9C']  # blue, red, green, purple, gray
  # or, for two-condition contrasts, often just blue vs gray:
  palette = ['#3B5BA5', '#7F7F7F']
  ```
- For "model vs data", the idiom is **data in black/dark gray points, model fit as a colored line**. Don't compete: let the data be the anchor.
- **But when the data IS the only thing on the figure** (no model overlay, no second condition), use a clear vivid color, **not gray**. "Data in gray" is a *don't-compete* rule for when a colored model fit is alongside; on a data-only figure it reads dull and unfinished. If the talk/paper has an established palette (illustrations, slide deck), match the panel color to *what's being measured* (e.g., red for an HP-distractor effect if the illustration uses red for HP). Make color carry semantic weight.

**Across both:**
- Use color to encode a variable, not to decorate. If two lines differ categorically and could be told apart by linestyle (solid vs dashed) or marker shape, do that and keep color free for a continuous variable.
- **Color is semantic across the whole figure, not just within a panel.** Once a hue means a condition in one panel (blue = cue-left in panel a), the reader reads it that way everywhere. If another panel collapses across that condition (grand-mean curve, aggregate bar), do **not** reuse the hue — switch to neutral gray, or the aggregate falsely reads as "cue-left data". In reverse: don't introduce a new hue for a condition that already has one elsewhere. Color persistence across panels is one of the strongest correctness signals in a paper figure.
- Test by converting to grayscale (`convert -colorspace Gray fig.pdf fig_gray.pdf`). If conditions become indistinguishable, the encoding leans too hard on hue — add linestyle or marker variation.
- Avoid pure red and pure green together (deuteranopia). The hand-picked palette above is safe.

## Error and uncertainty

How uncertainty is drawn is one of the strongest style signals.

- **Continuous predictors (psychometric / tuning curves)**: shaded ±1 SEM bands behind the line, same hue, alpha ~0.2–0.3, no edge. The default for `lineplot` with `errorbar=('se', 1)`. Confirm the band is behind the line (`zorder`), not on top.
- **Discrete conditions (bar / point plots)**: thin error bars with **no caps** or very short caps (`capsize=0` or `capsize=2`), `errwidth=0.8`. Default matplotlib's capped T-bars look amateurish at publication size.
- **Central tendency: mean ± SEM is the conference default** (VSS, OHBM, SfN — audiences read error bars as SEM unless told otherwise). Use it by default. But SEM is only meaningful when the **mean** is — i.e., when a few extreme outliers don't dominate. For heavy-tailed estimates (e.g., attention-field gains in low-SNR ROIs blowing up to |g| > 5 or 10), the mean gets pulled off the visible swarm and SEM balloons. Two honest fixes:
  - **Trim then mean ± SEM** with a fixed absolute or per-ROI cutoff (e.g., `|value| > 4`, or "drop subjects > 3 × IQR from the median"). Annotate `n_kept (−k_dropped)` under each x-tick AND state the trim rule in a small in-figure note (`Mean ± SEM · outliers |g| > 4 excluded`) so the audience doesn't read default-SEM into trimmed-SEM. The talk-friendly choice: expected stat, labeled deviation.
  - **Median + bootstrap 95% CI** (or HDI) — robust to outliers, matches the visible swarm exactly. Cost: the audience must read the label or they'll assume SEM. Only worth it if outliers are a substantive part of the story.
- **Make the central-tendency marker pop above the swarm.** A 13-pt diamond with a *thick dark edge* (1.5–2 pt) over translucent subject dots (alpha 0.3–0.4) reads as "this is the summary, those are the data". A 6-pt marker with thin edge in the dots' color disappears into the cloud. When SEM is genuinely small (SEM ≪ marker radius in data units), shrink the marker (e.g., 9 pt) to let the bars peek out — don't inflate the bars artificially.
- **Bayesian / posterior intervals**: shaded HDI bands rather than discrete bars whenever the predictor is continuous. See the dedicated section below for PyMC / `bauer` posteriors and seaborn's `errorbar`.
- **Bootstrap distributions or single-trial spread**: stripplot or swarmplot over point estimates, low alpha (0.3–0.5), small markers (size 2–3). Don't box-plot for n < ~20 per condition — show the points.
- **Always state in the caption what the error represents.** "Shaded regions show ±1 SEM across subjects" or "Error bars show 95% bootstrap CI". Non-negotiable, even if obvious to the author.

## Posteriors from PyMC / bauer

The convention for Bayesian posteriors: **posterior median (or mean) as
the central line, 95% HDI as a shaded band, 50% HDI as a darker inner
band when the figure can carry it.** Always say "credible interval" or
"HDI" in the caption — never "confidence interval", a different object
this audience cares about.

Plotting recipes (`arviz.InferenceData` → long-form DataFrame → seaborn
`lineplot` with HDI errorbars, the HDI-vs-equal-tailed distinction for
skewed posteriors, the forest-plot pattern for discrete per-condition
posteriors, and caption language) live in
[references/bayesian_posteriors.md](references/bayesian_posteriors.md).

**Posterior predictive checks** (model-simulated data over observed —
psychometric/chronometric curves, RT distributions, quantile-probability
plots) are a different panel with their own conventions: data as
anchoring markers, model as line + HDI band (never reversed), the band
built by summarizing **per posterior-predictive draw before** taking the
HDI so predictive uncertainty is preserved. Full recipes — the bauer
`model.ppc` / PyMC `sample_posterior_predictive` workflow, binning,
per-subject vs group PPCs, the "a PPC must be able to fail" rule — live
in [references/posterior_predictive_checks.md](references/posterior_predictive_checks.md).

## Axes: the details that matter

- **Tick locations are chosen, not defaulted.** Pick 3–5 ticks per axis, round numbers at meaningful values (lowest/highest stimulus levels, integer log-spaced values). Use `ax.set_xticks([...])` explicitly.
- **The data extremes belong on the axis.** Matplotlib defaults pick "round" interior ticks (10, 15, 20) and skip the actual endpoints (5 and 25), forcing the reader to infer the range. Always include the min and max as explicit ticks — for a 5–25 numerosity range, use `[5, 10, 15, 20, 25]`, not `[10, 15, 20]`. Same for any psychophysics axis (contrast levels, spatial frequencies, n-back levels): the extreme stimulus values are part of the design.
- **Align y-axes across panels that show the same quantity.** A row/column all plotting the same thing (Pearson r, proportion, cvR², SD) needs a shared y-scale, or the reader mis-reads a panel-specific "tall bar" as a real effect when it's just an autoscaled range. `sharey="row"` is the easy fix. *Exception*: a metric on a clearly different scale (a "delta"/"specificity" row 5–10× smaller than the panels feeding it) gets its own zoomed range — but say so in the row label, never autoscale silently. Compute y-limits **after** aggregation so they fit the rendered data, not pre-aggregated extremes.
- **Don't repeat N across panels if it's the same everywhere.** If every panel uses the same subjects, the N=… label belongs in one corner of the first panel (or the caption). Repeated N labels are noise.
- **Log axes**: when a variable spans orders of magnitude (contrast, frequency, numerosity), use log scale. Ticks at decadal values, minor ticks at 2, 5 between, minor tick labels hidden. Consider explicit `ScalarFormatter` to avoid scientific notation for values 0.01–100.
- **Trim the axis to the data.** `sns.despine(trim=True)` does most of this; verify the spine ends at the last tick, not past it.
- **Axis labels are short.** "Contrast" not "Stimulus contrast (Michelson)"; units in parentheses, qualifier in the caption: `Contrast (%)`, `Firing rate (spikes/s)`, `Reaction time (s)`, `WTP (CHF)`. See capitalization rule below.
- **Drop the axis label when the ticks already name the axis.** Self-describing categorical ticks — `["NPCl", "NPCr"]`, `["Mix shared-RF", "Sum", ...]`, `["sub-01", "sub-02", ...]`, `["V1", "V2", "V3"]` — make a category-type label ("ROI", "Model", "Subject", "Area") redundant. The ticks ARE the label. Default to **omitting categorical axis labels, adding one only when the category isn't obvious** (e.g. bare numeric ticks the reader can't interpret). When in doubt, set `""` and check whether anything was lost — usually nothing.
- **Y-labels short, statistical noise to the caption.** Long y-labels — "Mean ± SEM proportion of voxels with highest cvR²" — are the worst offenders. Shorten to the *quantity* ("Highest-cvR² fraction") and push central-tendency/error/n to the caption or a small in-panel note. "Bar + dots + error bar" already reads as mean ± SEM; spelling it out is text in service of nothing.
- **General rule: every piece of text must add information the data doesn't carry.** Applies to axis labels, annotations, titles, legend titles. Each time, ask "could the reader infer this from the data?" — if yes, cut it.
- **Math in labels: Unicode, not mathtext, when possible.** Matplotlib's `$...$` renders in Computer Modern by default and breaks Helvetica consistency. For Greek letters, subscripts, simple operators, put Unicode directly: `"σ (deg)"`, `"Δ contrast"`, `"log₂(numerosity)"`, `"R²"`. Reserve mathtext for structural math (fractions, integrals, summations); when needed, set `rcParams['mathtext.fontset'] = 'stixsans'` to keep it sans-serif, or `usetex=True` with a Helvetica preamble if the project uses LaTeX.
- **No grid lines.** None. If a reference value matters, draw it explicitly as a thin gray dashed `axhline`/`axvline` with `color='0.7'`, `lw=0.6`, `ls='--'`, `zorder=0`.

## Capitalization: first letter always

Every piece of text starts with a capital letter — axis labels, annotations, legend entries, panel titles, condition labels. Even two-word annotations: "Model fit", not "model fit"; "Stimulus onset", not "stimulus onset". The rest is lowercase unless a proper noun, acronym, or unit symbol (`Hz`, `CHF`, `RT`). The **one exception** is panel letters, which are lowercase (a, b, c, …) per Nature house style — see multi-panel layout.

Small but one of the strongest readability signals — mixed capitalization looks unfinished, lowercase-everywhere (the default) reads as informal. Consistency here is free; do it everywhere.

## In-panel annotations: guide the reader

In-panel annotations are how the figure carries its message without the caption. Don't make the reader hunt for the effect — point at it. The house style: short text labels with a thin curved arrow connecting the label to the relevant data feature. "Attention shifts the peak", "Model fit", "Stimulus onset", "Chance", "Inflection point". Two or three words. The figure becomes self-narrating: a reader skimming only the panels should extract the core finding from the annotations alone.

Use `ax.annotate` — it gives arrow plus text positioning in one call:

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
- **Curved, not straight.** `connectionstyle='arc3,rad=0.2'` gives the gentle hand-drawn arc that's a signature of the style. Adjust `rad` (0.1–0.3, signed) so the arrow doesn't cross data.
- **Thin and gray, not black.** `color='0.3'` or `'0.4'`, `lw=0.6`. Support the data, don't compete.
- **No arrowhead, or a very small one.** A plain line (`arrowstyle='-'`) often reads cleaner than `'->'`. Reserve arrowheads for when pointing direction is genuinely ambiguous.
- **Short text, capitalized first letter, no terminal punctuation.** "Model fit", not "model fit" or "Best-fitting model prediction." More than four or five words belongs in the caption.
- **Place text off the data.** Whitespace upper-right or lower-left is usually available. If the panel is dense, use a leader line into the margin.
- **One to three annotations per panel, maximum.** More and you've stopped guiding and started cluttering.

Use annotations to label: the key effect ("Peak shift", "Saturating nonlinearity"), the model ("Efficient-coding fit"), reference values ("Chance", "Veridical"), and time-series event markers ("Stimulus onset", "Response"). Don't repeat what the axis label already says.

## Multi-panel layout

Real papers have multi-panel figures. Default to `plt.subplots` for simple grids, `matplotlib.gridspec` when panels differ in size or share complex relationships.

- **Panel letters: a, b, c, d, …** (lowercase) in bold sans-serif, slightly larger than axis labels (10–12 pt), at the top-left **outside** the axes: `ax.text(-0.15, 1.05, 'a', transform=ax.transAxes, fontsize=12, fontweight='bold', va='bottom', ha='right')`. Same position across all panels — pick coordinates, reuse. Lowercase is the Nature/Nature Comms house style and the default here; uppercase (A, B, C) is the older Science / J Neurosci convention — use only when the target journal requires it. Panel letters are the **one exception** to "every piece of text starts capitalized" — caption references match ("see panel a", not "panel A").
- **Don't waste space.** `plt.tight_layout()` is a reasonable start; `constrained_layout=True` at figure creation is better. If panels share an axis, use `sharex=True`/`sharey=True` and remove redundant tick labels.
- **Align axes across panels.** Two panels showing the same quantity (both firing rate) need the same y-range *and* the same y-label position. Eyes shouldn't recompute scale across panels.
- **Aspect ratio per panel.** Most data panels look right between 1:1 and 4:3 (width:height); time-series wider (2:1 or 3:1). Avoid tall-thin panels unless plotting something genuinely vertical (population stack, anatomical depth).

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

Save both PDF (direct submission) and SVG (post-processing). Never save the final figure as PNG for a paper unless required.

Check the output: open in a PDF viewer at 100% zoom and confirm (1) text is selectable (font embedded as text, not paths), (2) lines are crisp at target print size, (3) nothing is clipped at the edges.

## Iterating with the user: the refinement loop

Real figures are *refined* over many small rounds ("make the dots bigger", "the legend overlaps", "centre that title"). The naive loop — edit → render → rasterize PDF to PNG → **read the image to judge** → repeat — is slow, burns tokens, and makes the assistant the bottleneck on a task where the user is the faster, better judge. The key realization: **the user has a PDF viewer open and sees the result instantly; you don't need to look at every change.** Re-rasterizing and reading an image on every tweak duplicates judgment the user is already making in real time.

Divide labor by *who is the right judge*, not by habit:

| Check | Best judge | Why |
| --- | --- | --- |
| Aesthetics — spacing, balance, "looks better?" | **The user** | Faster, taste is theirs, viewer already open |
| Geometry you can't reason about blind — does X overlap Y, are columns aligned across separately-saved panels | **You, reading the image once** | Genuinely needs a look |
| Objective rules — font ≥ min pt, embedded editable fonts, RGB, exact page size, ≥ 0.5 pt lines | **A `verify.py` script** | Deterministic; no eyes needed |
| Cross-cutting consistency — only-Helvetica, capitalization, colour persistence across panels | **Background agents, in parallel** | Off the critical path |

Concrete setup that makes this work:

1. **Render-on-save watcher.** Wire a file watcher (`watchexec`, `entr`, `fswatch`) on the figure-script directory so saving a script re-renders just that figure's PDF; editing a shared style module re-renders all. Then *nobody runs a render command* — the PDF refreshes in Preview/Affinity/the IDE and the assistant drops out of the render loop. A ~15-line `watch.sh` calling `watchexec --postpone --watch <figdir> --exts py -- <render-the-changed-module>` is enough; render the most-recently-modified script to avoid fragile change-event parsing.
2. **Stop reading images by default.** Make the edit, let the PDF update, let the user react. Pull an image into context only when (a) the user asks "what do you think?", or (b) you must verify a geometry claim you can't reason about from the code.
3. **Batch tweaks into passes.** Have the user fire a *list* of changes ("dots bigger in 1B/1C, box the legend in 4, fix the p-value overlap in 5") and apply them in one pass with one render, not one round-trip per tweak. Cross-cutting asks ("harmonize dot sizes everywhere") are one edit when the style lives in a shared module — the main reason to centralize `set_style()` / palette / shared geometry in one importable place.
4. **A contact sheet for the rare all-at-once look.** When you *do* need to see everything (final QA, or a holistic opinion request), tile every panel into one image rather than reading them one by one: `sips`/`pdftoppm` each PDF to PNG, then `montage *.png -tile 4x -geometry 320x -label '%t' sheet.png`, and read that single image.
5. **`verify.py` is the gate, not your eyeballs.** A tiny script that walks the output PDFs and asserts the objective rules (min font size — matrix-aware so rotated tick labels aren't mis-measured; fonts embedded as Type-42 not Type-3 paths; RGB; page size in mm; line weights) catches regressions humans miss, in a second per pass.
6. **Cached source data = free restyling.** Cache each panel's expensive computation (model fits, posterior draws, large aggregations) to a small source-data file the plotting code reads; then *form* iteration never re-runs the *stats*. This makes rounds 2-N cheap and is worth setting up early.

Net shape: **the user is the aesthetic judge with a live-updating preview; the assistant is editor plus objective QA plus parallel auditor.** If you catch yourself rasterizing-and-reading after every small change, stop — that's the smell of the wrong judge in the loop.

Full pipeline — watcher script, `verify.py`, contact-sheet and background-agent recipes — lives in [references/refinement_pipeline.md](references/refinement_pipeline.md).

## What to ask the user before plotting

Before generating a figure from scratch, briefly confirm:
- **Target medium**: paper (which journal/column width?), talk, poster, preprint? Sets the figure size.
- **Number of panels** and what each shows.
- **The variables**: what's on x, y, color/style, facet?
- **What the error/uncertainty represents** — across-subject SEM, within-subject CI, bootstrap, posterior?

If the user hands over a dataframe and says "plot it", use reasonable defaults from the principles above and state the assumptions so they can correct course.

## Anti-patterns to avoid

These come up constantly and are worth refusing by default:

- Default `tab10` / `Set1` / `Set2` palettes
- Top and right spines still present
- Inward ticks (matplotlib default, looks wrong)
- Legend with a frame, especially inside the plot area on top of data
- Title on the axes (`ax.set_title`) for paper figures — titling belongs in the caption. Talks/posters differ.
- Grid lines as background decoration
- 3D plots, pie charts, dual y-axes — essentially never appropriate for vision-science papers
- PNG output for the final figure
- Bar plots with n < 10 per condition and no individual points shown
- The same hue at different saturations to encode unrelated categorical variables
- Capped error bars at small print size (caps add noise, not information)

## Final pass: does this figure work?

Before saving and presenting, step back and verify:

1. **Can I state the figure's point in one sentence?** If not, it has no story yet — decide what it's trying to say before polishing.
2. **Does the panel order match the argument?** Panel a reads first, then b, then c. The eye travels through the science in argument order.
3. **Cover the caption. Does the figure still convey the main finding?** The hard test. If covering the caption breaks comprehension of the *finding* (not bookkeeping — n, error metric, test are fine in the caption), add in-panel annotation: label the effect, name the model fit, mark the reference value. The panels must carry the message.
4. **Does the caption carry the bookkeeping?** Define every abbreviation, state every error metric, give n, name the statistical test. The caption isn't where the message lives, but it's where readers find the details to trust it.
5. **Is there anything that isn't data or essential reference?** If yes, remove it.

A figure passing these five is done. Spines, palettes, and ticks earn the figure the right to be looked at — but they don't make it say anything.

## When to deviate

Style serves communication, not the reverse. Deviate when:
- The data genuinely requires a non-standard encoding (circular variables → polar plot, rare as polar plots are in this tradition)
- The journal's style guide conflicts — follow the journal
- A talk audience won't read 7pt labels — scale up via `sns.set_context('talk')` rather than fighting the rcParams

Document the deviation briefly in a code comment so the next person (or future you) knows why.
