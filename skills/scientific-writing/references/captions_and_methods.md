# Figure captions and Methods

---

## Figure captions

### Anatomy

```
Fig. N | <Declarative title naming the finding>. <a> <what is plotted>;
<how it was computed>; <what the error band is>. <b> …  <Closing clause
stating the takeaway for the panel that carries the claim.>
```

Attested, in full:

> **Fig. 5 | Decoded parietal payoff representations predict noisiness and bias in
> choice.** a Numerical population-receptive-field (nPRF) mapping reveals
> non-linearly tuned, numerosity-sensitive BOLD responses around the intraparietal
> sulcus, closely following the ROI drawn on an independent data set; shown is the
> average preferred numerosity across participants in fsaverage space, separately
> for the 3T and 7T sessions. b Per-participant decoding correlations for each
> scanner (3T, 7T): (i) decoded posterior mean versus objective log-numerosity
> (decoding accuracy) and (ii) decoded posterior s.d. versus absolute decoding
> error (uncertainty calibration). Each point is one participant (swarm), the
> white diamond is the mean ± 1 s.e.m., and the dashed line marks r = 0. Nearly
> all participants show a positive decoding correlation (27/30 at 3T, 29/30 at
> 7T), and the width of the decoded posterior predicts the objective error of its
> mean (two-sided one-sample t-tests against zero across participants, n = 30;
> decoding accuracy t(29) = 7.1 (3T) and 8.0 (7T); …; all p < 0.001, uncorrected).

The preprint variant uses lettered run-ins with a short bolded-in-prose panel
title before the explanation:

> B) Noise as a function of magnitude. Fitted representational noise ν increases
> sublinearly with objective payoff. Solid lines show … Shaded areas are 95%
> credible intervals of the group-level estimates.

### Always present

- **The title is a claim**, not a label. "Task paradigm and order × stake effects
  on risky choice", "Formal model comparison (ELPD)", "Decoded parietal payoff
  representations predict noisiness and bias in choice".
- **n**, stated in the caption even when it is in the Methods — per panel if it
  differs.
- **What every band, bar and whisker is.** The caption *closes* by saying what
  the error bands are. "Error bars denote ±1 s.e.m. across participants (n = 30)";
  "dots are per-participant posterior means and lines the 95% credible
  intervals"; "Open circles show each model's ELPD ± 1 standard error (SE); grey
  triangles show the ELPD difference ± its standard error (dSE)".
- **What each reference line marks.** "the dashed line at 0.5 indicates
  indifference"; "the dashed vertical line marks the risk-neutral ratio
  (1/0.55 ≈ 1.82)"; "the dashed line marks r = 0".
- **The test and its sidedness**, plus whether correction was applied — including
  when it deliberately wasn't, with the reason: "order effects are reported as
  one-sided posterior probabilities, so no multiple-comparison correction
  applies"; "no correction for multiple comparisons"; "uncorrected".
- **The colour mapping**, when hue carries a variable: "coloured by each
  participant's combined risk profile (risk-seeking/risk-averse/risk-neutral)";
  "separately per presentation order (hue)".

### Honest disclosure in captions

A schematic panel says it is a schematic and that no test was run:

> "d is illustrative, using stereotyped parameter values; it shows no data, and
> no statistical test was performed."

A panel that greys out models which cannot in principle show an effect says why:

> "Models that cannot distinguish the two presentation orders (Models A, B and D)
> are plotted in grey; only Model C, which allows order-dependent noise, retains
> the Safe-first/Risky-first colours."

A caption naming a probit-derived quantity says the probit produced it: write
"parameters of a probit fitted to the choices", not "risk attitude and choice
consistency" unqualified. (This is Rule 0 applied to captions.)

### Pointers to the supplement

End the relevant panel's clause, not the whole caption: "See Supplementary Fig. 2
for the two sessions analysed separately."

See the **scientific-figures** skill for the figure itself — in particular the
rule that the panels alone must carry the story, which means the caption is
bookkeeping and never the place where the message lives.

---

## Methods

### Subsection order

Stable across papers:

1. Participants and ethics
2. Procedure (session structure, payment)
3. Experimental paradigm (trial timeline, stimuli, geometry)
4. Apparatus / display (per scanner)
5. Behavioural analyses — one sub-block per model, each with a bolded run-in
   `Model specification.` / `Model estimation.` / `Model comparison.`
6. MRI acquisition parameters (per field strength)
7. Preprocessing
8. Encoding-model fitting / decoding
9. Data and code availability

### Conventions

**Every duration, size and count is exact**, with units, and jitter is listed
rather than summarised:

> "a pie chart with a diameter of 1 degree-of-visual-angle (dova) was presented
> for 300 ms … The coins had a radius of 0.3 dova and were all randomly
> positioned with their centre within a circular aperture with a diameter of 5.25
> dova. The coin stimulus array was presented for 600 ms, after which only the
> fixation cross was presented for a jittered duration of either 5, 6, 7, or 8 s."

**Design choices are justified inline**, not asserted:

> "The screen always contained a red cross with two diagonal lines to keep
> fixation near the centre of the screen and to not confound the numerosity of
> stimuli like a standard fixation cross or point might."

**External models are attributed, then abbreviated:**

> "Khaw et al. showed that in risky choice paradigms where participants choose
> between a certain payoff C and a risky payoff X with a probability of payout p,
> observed choice behaviour can be understood as the outcome of a Bayesian
> inference process. Specifically, their model (from here on referred to as KLW
> model) assumes that …"

**Reparameterisations state their purpose:**

> "Thus, to aid parameter estimation and improve model interpretability, we
> reparameterize the model as follows: …"

**Sampler settings, priors, convergence criterion and the model-comparison method
are all stated.** Absence of any of these is a Methods gap worth flagging:

> "Posterior estimates were obtained using the NUTS-sampler, as implemented in
> pymc 5, with a target acceptance rate of 90%."
> "We used mildly informative priors on all group distribution parameters: …"

The **bayesian-workflow** skill covers what to report and when a fit has earned
the sentence.

**Collected-but-unanalysed data are declared**, not silently dropped:

> "The results from this certainty rating are not presented in this paper."
> "to allow for both eye-tracking (3T; data not presented here) as well as
> ultra-high resolution imaging (7T)"
> "These data were not analysed in the present study."

**Participant exclusions are reported as a flow with a total**, and the selection
criteria are given:

> "Thus, out of 78 participants, 35 met the inclusion criteria and were invited
> for two additional sessions."

**Ethics boilerplate** — the attested form, including the sex/gender statement
Nature journals now require:

> "The study was not designed to investigate sex or gender differences, and no
> sex- or gender-based analyses were performed. All participants gave written
> informed consent before taking part, in accordance with the Declaration of
> Helsinki, and were free to withdraw at any time. The study protocol was approved
> by the Cantonal Ethics Committee of Zurich."

**Reparameterisation and equation prose** stays in the same voice as the rest —
"Thus, ρ determines to which extent all voxels correlate with each other" — so
the reader can follow the algebra in words as well as symbols.

### What belongs in Methods rather than Results

A known trap from the TMS project: a sampling difficulty that turns out to be a
statement about what the design can identify belongs in Methods (Model
estimation), stated as a limitation of identifiability, **not** as "the
alternative model cannot be fitted" — because a reviewer who refits it will find
that it can:

> "At the two-parameter power form, the position-indexed parameterisation does
> not sample reliably: its low anchor falls at the bottom of the payoff range,
> where presentations are almost all safe options, so it trades against the mean
> of the safe magnitude prior — the least well-identified parameter in the model
> … The stage-indexed parameterisation shares one perceptual component between the
> two options and is not subject to this trade-off; with four or more spline
> anchors the position-indexed models sample cleanly and give the same answer."

The general rule: name the cause, make it checkable, and turn the sampling
annoyance into a statement about the design. Never claim a model "cannot be
fitted" when it converges under some parameterisation.
