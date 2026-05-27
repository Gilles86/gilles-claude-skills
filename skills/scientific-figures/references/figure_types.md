# Figure-type cheat sheet

**When to load:** starting a panel of a specific common type
(psychometric, time series, point/bar comparison, scatter, heatmap)
and want the specialization of the main skill's universal rules.

The conventions in the main skill are generic; here's how they
specialize for the figure types that come up most.

## Psychometric / tuning curve panel

- Data points: black or dark gray, size proportional to n if n varies
  across stimulus levels (`s=n*scale`), error bars (vertical only, no
  caps, lw=0.8).
- Fit: colored line (one color per subject or condition), 1–1.5 pt,
  smooth (evaluate at 200+ x-values).
- X-axis often log-scale (contrast, frequency, numerosity).
- Y-axis: probability (0 to 1) or proportion (0 to 1), with ticks at
  0, 0.5, 1.
- Reference lines: `axhline(0.5)` for chance in 2AFC, thin gray dashed.

## Time series / event-locked average (PSTH, BOLD timecourse, pupil trace)

- Mean as a line, ±SEM as a shaded band of the same hue.
- Vertical reference lines at event onsets (`axvline`, thin gray,
  dashed if not a hard event).
- X-axis label includes the lock event: "Time from stimulus onset (s)".
- For multiple conditions, all on the same axes with direct labels at
  line endpoints, not a legend.

## Comparison of conditions (bar / point plot)

- Prefer pointplot or stripplot+pointplot over bar plot when n is
  small (< ~30).
- If using bar: thin (`width=0.6`), unfilled or light fill with
  darker edge, error bars uncapped.
- Always show individual data points as a swarm or strip overlay when
  subjects ≤ 30 — readers want to see the n and the spread.
- Connect within-subject points with thin gray lines (`lw=0.5`,
  `alpha=0.4`) in repeated-measures designs.

## Scatter (correlation, model vs data, individual-difference)

- Filled circles, single color, size 15–25, edgecolor white or none,
  alpha 0.6–0.8 if many points.
- Identity line (`x = y`) as thin gray dashed when comparing two
  measurements of the same quantity.
- Regression line only if statistically meaningful; report r/r² in
  the panel as a small text annotation, not in a legend.
- Equal aspect ratio (`ax.set_aspect('equal')`) when both axes are
  the same quantity.

## Heatmap (RDM, similarity matrix, model coefficients)

- `vlag` or `RdBu_r` for divergent, `mako` or `viridis` for unsigned.
- Square cells, no internal gridlines, no annotations inside cells
  unless n × n is small (< 8).
- Colorbar: thin (`shrink=0.6`), outside the plot area, with a short
  label.
- For RDMs specifically: symmetric, square aspect, hide the upper
  triangle if redundant.
