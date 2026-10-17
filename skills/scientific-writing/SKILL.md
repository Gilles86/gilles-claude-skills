---
name: scientific-writing
description: Draft and revise manuscript prose in Gilles's voice — abstracts, introductions, results, discussions, methods, figure captions, and response-to-reviewer letters for cognitive-neuroscience / neuroeconomics / vision-science papers. Encodes the argument architecture, sentence habits, hedging asymmetry, statistics-reporting conventions and epistemic discipline measured from his first-author papers. Use whenever writing or rewriting manuscript text, when asked to "write the intro", "draft the abstract", "tighten this paragraph", "make this sound like me", "write the discussion", "rewrite this caption", "respond to reviewer 2", or when editing a .docx/.tex/.md manuscript draft. Pairs with **scientific-figures** (which makes the figures these captions describe) and **bayesian-workflow** (which decides whether a result has earned the sentence you are about to write about it).
---

# Scientific writing, in Gilles's voice

This encodes a measured style, not a generic one. It was derived from the
first-author corpus described in
[`references/corpus_and_evidence.md`](references/corpus_and_evidence.md), weighted
towards the most recent papers Gilles actually wrote — above all
*Rapid changes in risk attitudes* (Nat Commun 2026) and the TMS-fMRI preprint
(2025). Co-authored papers where he did not drive the writing are **excluded from
the voice model** and listed there so the corpus can be audited and extended.

When something below is thin or uncertain, it says so. Don't invent rules.

---

## Rule 0: never invent a number, and never let a model's summary pose as a measurement

This is the rule that outranks every stylistic preference here. Violating it
produces text that is worse than badly written — it is wrong.

**Never write a number you did not read from an artifact.** Not a rounded one,
not a "roughly", not an interpolation from a figure. If the value is not in the
handover notes, the fit output, or the existing draft, write a bracketed
placeholder and list it at the end of the response:

```
⟦TODO: group-mean decoding r, 7T session⟧
⟦BB_INTERVAL⟧          ← a token that already has a substitution table
```

Keep the brackets intact, never split a token across a line, and surface every
token you introduced so it can be checked against the substitution table. If a
fit has not converged, leave the brackets and write no number at all — an
unconverged parameter has no value to report.

**Name the model when the model is doing the work.** The only condition-free
observable is the thing that was actually recorded — choice proportions,
response times, estimates. Everything else is a summary computed *through* a
model, and the sentence must say so:

> ✅ "The model reproduces the pattern of the cTBS effect on choice and about
> half its magnitude (predicted +0.025 against an observed +0.053 for
> risky-second trials). Summarising both observed and simulated choices with the
> same probit locates the shortfall: the model captures the reduction in slope
> but not the accompanying shift in the fitted indifference point."

> ❌ "cTBS made participants more risk-seeking by 0.049." — the RNP was not
> measured; a probit produced it, and a different link family would split the
> same curve difference differently.

Corollary: any summary applied to simulated data must be applied **identically**
to the observed data before the two are compared, and the prose should make that
symmetry visible.

**Don't let a weaker piece of evidence carry a stronger claim.** If model
comparison establishes three things, write three; if the fourth is carried by
posterior predictive checks, attribute it to the checks. See the
**bayesian-workflow** skill for what a fit has actually earned.

---

## The voice in one paragraph

First-person plural, active, present-tense for what models and figures *do*,
past-tense for what *we* did. Sentences are medium-long (median 18–26 words) and
unafraid of a colon, a parenthesis and a subordinate clause in the same breath —
but they always resolve. Claims are confident at the headline and scrupulously
scoped in the qualifier. The argument moves by explicit connectives rather than
by juxtaposition, and every paragraph earns a "thus" sentence. Nothing is
ornamental: no exclamation marks, no mid-paragraph bold, no bullet lists in
Results.

## The reframing engine

Almost every first-author paper runs the same intellectual move, and getting it
right matters more than any sentence-level tic:

> **A phenomenon that a field explains with a stable trait, preference or
> valuation process is re-derived as a consequence of noisy inference on
> capacity-limited representations.**

The machinery of that move:

1. **Name the incumbent field and its account, fairly and formally.** Not "prior
   work assumed" — "Neoclassical economic theories describe such individual
   differences using the concept of individual risk preferences: An individual
   would be risk-averse if they prefer to obtain for sure the expected value of a
   risky prospect…" Give the incumbent its actual definition. The reframing only
   lands if the reader believes you understood what you are replacing.
2. **Import the mechanism from a named neighbouring field**, usually perceptual
   neuroscience or Bayesian psychophysics, and carry its normative justification
   across: a bias is *optimal given the constraint*, never a failure. "Note that,
   on average, such biases are beneficial because they reduce the average
   perceptual error."
3. **Keep the alternative cheaper than the incumbent.** The point is that no
   subjective-valuation process is needed, not that a richer one is.
4. **Scope the conclusion honestly at the end.** "While this evidently does not
   prove that subjective valuation is not involved in risky choices, it still
   suggests that perception may play an important role and needs to be accounted
   for explicitly…"

Recurring closing ladder: mechanism → domain → policy or clinic. The last
Discussion paragraphs of the 2026 paper go from parietal population codes to
pathological gambling to how banks elicit client risk preferences. Reach is
earned at the end, never claimed at the start.

## Argument architecture

Full move-by-move templates with attested examples live in
[`references/section_moves.md`](references/section_moves.md). The skeleton:

**Introduction** — five moves, ending in a distinctive *triple*: the "Here, we…"
paragraph, then an explicit roadmap paragraph ("In the following, we will first
describe…"), then a preview paragraph ("Previewing our results, stimulation
reduced the fidelity of…"). Most papers have one of these three; his have all
three, and reviewers never complain about it.

Rhetorical questions in the Introduction are load-bearing, not decorative — each
one maps onto a Results subsection, and they are usually enumerated: "First, what
determines…? Second, … Finally, where do these apparent fluctuations come from?"
If you write a question, you owe it a subsection.

**Results** — subsection headings are **declarative claims with a full
predicate**, often 10–15 words:

> Different noise contexts shift risk attitudes as predicted by Bayesian inference on noisy payoff representations
> Decoded payoff representations in parietal cortex predict noisiness and bias in choice
> Shifts in risk preference are driven by increased noise in small- but not large-magnitude representations

Never "Behavioural results", never "fMRI analysis".

Within a subsection the order is fixed: **hypothesis → why this analysis can test
it → what we found → what it means.** The prediction is stated *before* the
number, so the result can be met with "In line with our predictions, …". Each
subsection closes with a flagged summary — "In sum,", "In summary,", "Thus,",
"Taking stock,", "In conclusion," — and section transitions are explicit and
forward-looking: "We now turn to more mechanistic computational models of choice
to better understand this empirical pattern."

**Discussion** — restate the contribution, then numbered implications ("First,
…"; "A second key implication of our study…"), then self-anticipated objections,
then future work as *concrete designs*, then the reach ladder, then a one-
paragraph "To conclude, …".

**Objections get their own paragraph and are conceded before they are
answered.** This is a signature, not a formality:

> "One question about our model might be whether it is unnecessarily complex, as
> it contains relatively many parameters to fit the data. We addressed this
> question with both qualitative predictive checks and quantitative model
> comparison techniques…"
>
> "A related critique of Bayesian theories, and potentially the PMCM, is that
> they are not mechanistic models of neural function but rather prescriptive
> models of information processing. Nevertheless, …"

Future work is specified, never gestured at: "future work might employ different
paradigms with a more continuous behavioural measure, such as
willingness-to-pay" — not "further research is needed".

## Sentence-level signature

**The colon followed by a capital letter.** The single most identifiable tic, and
the workhorse of explanation: state the claim, colon, unpack it. Measured at
90% of colons in the TMS preprint and 43% in the 2026 Nat Commun paper, against
11–20% in papers he didn't write. Capitalize the word after the colon.

> "This regressive bias is far from arbitrary but reflects an optimal Bayesian
> strategy: When information is uncertain or noisy, our brains rely more on prior
> beliefs to reduce errors."
>
> "Our previous work has shown that individual differences in the acuity of
> parietal magnitude coding predict individual differences in risky choice
> behaviour: Participants with noisier payoff magnitude representations tend to
> resort more to their prior beliefs and are, on average, more risk-averse."

**The em dash is reserved for the appositive definition of the paper's central
construct**, typically in the abstract's first sentence. It is not a
general-purpose connector — the colon does that job.

> "Risk attitudes—the willingness to accept uncertainty for larger potential
> rewards—are often treated as a stable individual trait, yet…"

**Sentence-opening connectives carry the argument.** The attested set, with the
important distinction: `Critically,` `Crucially,` `Importantly,` `Notably,` are
**load-bearing and reserved for the design feature that makes the inference
possible**, not sprinkled for emphasis:

> "Crucially, the payoffs of the safe and risky options were presented
> sequentially."
> "Critically, this model disentangles choice consistency from preference,
> avoiding the confounds inherent in raw choice proportions."

If the sentence would survive deletion of the adverb with no loss, delete the
adverb. Rough budget: two or three per section, not per paragraph.

The workaday connectives — `Thus,` `However,` `Moreover,` `Furthermore,`
`Indeed,` `Specifically,` `Conversely,` `In line with` — are used freely and are
what makes the prose feel argued rather than listed. Full inventory with
frequencies in [`references/phrasebank.md`](references/phrasebank.md).

**`Note that …`** is his parenthetical-caveat device, about three or four per
paper, used for technical points a careless reader would miss — model
equivalences, analysis choices, scope limits:

> "Note that this model A is equivalent to a standard probit psychophysical model."
> "Note that we refrained from analyzing raw choice proportions since they cannot
> be interpreted cleanly in isolation."
> "Note that the psychophysical model we use here is a measurement model and thus
> remains agnostic to the precise underlying mechanisms."

**Reasoning is enumerated inline**, in prose, not as a bullet list: "This pattern
follows from two properties of the fitted model. First, … Second, …"

**Everyday instantiation, in threes.** Abstractions get grounded in a triplet of
concrete examples: "more willing to become self-employed, engage in new
relationships, or to invest money in the stock market"; "just as some people
particularly dislike electronic music, others may particularly dislike taking
risks". Two examples feel thin, four feel padded.

**Hedging is asymmetric.** Results are stated flatly; interpretations are hedged.
"We found a very robust decrease in risk aversion after cTBS" — no hedge. "This
suggests that a single trait may underpin both…" — hedged. Never hedge a
credible result, never state an interpretation flatly. The scope qualifiers he
actually uses: *at least partly*, *at least under some conditions*, *at least in
the small-stake laboratory experiments widely used in the field*, *can be rooted
in*, *may*, *in line with*, *broadly consistent with*, *this does not prove … but
it suggests*.

## Vocabulary: reuse, don't paraphrase

Elegant variation is the enemy. A construct keeps exactly one name through the
whole manuscript. The core lexicon:

> magnitude representations · choice consistency · risk attitudes ·
> neurocognitive · the parietal ANS · representational noise · acuity ·
> presentation order · payoff magnitudes · indifference point · regressive bias ·
> central tendency (CT) bias · prior expectations · perceptual inference ·
> mechanistically · population receptive field (nPRF) · decoded posterior

If a draft alternates "noise", "imprecision", "variability" and "unreliability"
for the same quantity, that is a bug — pick the one the model parameter is named
after and use it every time. Genuinely different quantities get genuinely
different words (noise ≠ variability ≠ bias), and the prose should make the
distinction visible rather than blur it.

Every abbreviation is defined at first use **in each of** abstract, introduction
and methods independently, by immediate parenthetical gloss: "continuous
theta-burst transcranial magnetic stimulation (cTBS)", "the risk-neutral
probability (RNP)", "degrees of visual angle (dova)". External models are named
after their authors, then abbreviated: "Khaw et al. showed that… (from here on
referred to as KLW model)".

## Reporting statistics

Inline, in parentheses, comma-separated, and **always with an interval**:

```
(r(33) = 0.76, p < 0.001)
(r(28) = −0.500, p = 0.005, 95% CI [−0.73, −0.17])
(t(29) = 7.1, p < 0.001, 95% CI [0.13, 0.23])
(slope from 3.02 [95% CI: 2.73, 3.31] to 2.33 [2.07, 2.61], pBayesian < 0.001)
(average RNP of 58.0% for lowest stakes, 95% CI 48.2–67.3%)
```

Conventions:

- Bayesian quantities are reported as **one-sided posterior probabilities**,
  written `pBayesian`, with an explicit note that no multiple-comparison
  correction applies because they are not frequentist tests.
- Model comparison is reported as **ELPD plus the difference in units of its
  standard error** — "the difference in ELPDs is at least 21 standard errors" —
  and, where available, a **stacking weight** ("model weight of 95%").
- Parameter recovery and split-half reliability are reported as ranges of
  correlations, in the Results, not buried in supplements: "the six parameters
  were all correlated across the two sessions, with correlation coefficients
  r(28) between 0.46 and 0.76".
- A result reported for two sessions/scanners is reported for **both**, with both
  values, rather than pooled silently.

## Figure captions and Methods

Both have their own conventions — caption structure, what must always be stated,
Methods subsection order, and the honest-disclosure habits (declaring collected-
but-unanalysed data, flagging illustrative panels) — in
[`references/captions_and_methods.md`](references/captions_and_methods.md).

The two rules worth repeating here: a caption **always closes by saying what the
error bands are**, and a panel that shows no data says so ("d is illustrative,
using stereotyped parameter values; it shows no data, and no statistical test was
performed").

## Anti-patterns

Things that instantly read as not-him:

- **Bullet lists in Results or Discussion.** Enumerate in prose.
- **Bold for emphasis mid-paragraph.** The sentence should do the work.
- **Exclamation marks.** Zero across the corpus.
- `Crucially`/`Importantly`/`Notably` as filler rather than as a pointer at the
  design feature that licenses the inference.
- **Topic-style Results headings** ("Behavioural results", "Imaging results").
- **Hedging a credible result**, or stating an interpretation flatly.
- **Elegant variation** — three names for one construct.
- **A named effect size with no interval.**
- **"Further research is needed"** and other unspecified future work.
- **Signposting the draft doesn't already use.** When revising, match the
  existing register; don't import scaffolding from a different journal's style.
- LLM register generally: *delve, tapestry, landscape, realm, multifaceted,
  holistic, pivotal, cutting-edge, paradigm shift, it is important to note*.
  None occur in the corpus. (Note the contrast: *elucidate*, *well-known*,
  *robustly*, *showcase*, *dovetail* and *shed light* **do** occur and are fine —
  don't over-prune.)

## Spelling and mechanics

British vs American spelling in the corpus is **journal-imposed, not personal** —
his own drafts are American (`behavior`, `modeling`), Nature-family production
converts them. So: pick one per manuscript, state which, and be consistent; if
there is no stated target, default to the existing draft's choice, and to
American for a new document.

Serial comma: used. Sentence case for headings. `Fig. 1a` in running text,
`Fig. 1 |` in the caption itself.

---

## Workflow

**When revising an existing draft** — the usual case — work as
**before/after replacements of existing sentences, never as fresh paragraphs.**
The draft is the style reference; this skill is the checklist. Return the revised
text **section by section with a short note on what changed**, not a diff, and
end with the list of every `⟦TOKEN⟧` introduced.

**When drafting from scratch**, write the Results subsection headings first as
declarative claims. If a heading can't be stated as a claim, the analysis isn't
finished, and that is worth saying out loud rather than writing around.

**Before returning any text**, run the mechanical pass in
[`references/revision_checklist.md`](references/revision_checklist.md). It catches
the things that are cheap to check and expensive to miss: invented numbers,
unattributed model summaries, intervals missing from effect sizes, filler
adverbs, drifting terminology, and results stated with hedges.

## References

| File | What's in it |
| --- | --- |
| [`corpus_and_evidence.md`](references/corpus_and_evidence.md) | Which papers the voice was measured from, their weights, what was excluded and why, and the measured frequencies behind the claims above. Read this before adding a rule. |
| [`section_moves.md`](references/section_moves.md) | Move-by-move templates for abstract, introduction, results, discussion, with attested sentences for each move. |
| [`phrasebank.md`](references/phrasebank.md) | The attested connectives, transitions, objection openers, summary flags and closers, with frequencies and source papers. |
| [`captions_and_methods.md`](references/captions_and_methods.md) | Figure-caption anatomy and Methods conventions, including the honest-disclosure habits. |
| [`revision_checklist.md`](references/revision_checklist.md) | The mechanical pass to run before returning text. |
