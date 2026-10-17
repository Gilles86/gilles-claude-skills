# Corpus and evidence

The style rules in `SKILL.md` were measured, not guessed. This file records what
they were measured from, what was deliberately left out, and the numbers behind
the claims — so the rules can be audited, and so the corpus can be extended
correctly when new papers appear.

Source: PDFs under `~/git/gilles86.github.io/assets/pdfs/publications/<year>/`,
text extracted with `pdftotext -layout`. Reference lists were cut before
counting; two-column PDF extraction interleaves columns, so *sentence-level*
counts are approximate while *token* counts are reliable.

## Weighting

The voice is Gilles's, so authorship position drives the weight. Co-authored
papers where he did not drive the writing are excluded from the voice model
entirely — they are good papers, but they are somebody else's prose.

### Tier 1 — the voice (weight these)

| Paper | Year | Venue | Position | Why it counts |
| --- | --- | --- | --- | --- |
| `trial_to_trial_risk_fluctuations` | 2026 | Nature Communications | **sole first** | Most recent sole-first paper, fully developed argument, peer-reviewed and copyedited. The primary reference. |
| `tms_risk` | 2025 | bioRxiv preprint | **co-first** (with Moisa; GdH wrote it) | Uncopyedited — the purest sample of his own mechanics. Where the two disagree on spelling/punctuation, this one shows the habit and the Nat Commun one shows production overrides. |

### Tier 2 — partial (confirmatory only)

| Paper | Year | Venue | Position | Caveat |
| --- | --- | --- | --- | --- |
| `neural_priors` | 2026 | Nature Communications | co-first (Prat-Carrabin) | Shared drafting; the Nature-abstract register and present-tense Results are Prat-Carrabin's. Use for structure, not sentence habits. |
| `numrisk` | 2023 | Nature Human Behaviour | co-first (Barretto-García) | Shared drafting. The flagship result but not a clean voice sample. |
| `stress` | 2025 | bioRxiv | co-first (Renkert) | Shared drafting. |
| `odcs` | 2021 | NeuroImage | sole first | Sole-first but pre-Zurich (Knapen lab, vision science). Useful as a baseline for what is stable across topics. |

### Tier 3 — historical consistency check only

Sole-first papers 2014–2017 (`imagers_fallacy`, `qsm_gradual`,
`subcortical_cocktail`, `tdcs`, `ways_of_linking`, `fmri_comparison`). Used only
to confirm that a tic is career-long rather than recent. Not a source of rules —
the topic, the field and the seniority are all different.

### Excluded from the voice model

Papers where Gilles is a middle or second author and did not drive the writing.
Listed explicitly because it is easy to re-include them by accident when the
corpus is refreshed:

`probability_distortions` (2025, Bedi first — confirmed by Gilles as *not* his
writing), `sequential_representations` (2026, Bedi), `multisensory` (2025, Bedi),
`ofc_value` (2026, Le Bouc), `psilocybin` (2025), `attend_ignore` (2024,
Failing), `retinotopic_reference_frame` (2023), and all the Forstmann-lab
middle-author papers.

These were measured anyway, as a **control group**: the tics that separate Tier 1
from this set are the ones that are actually personal. That contrast is what
makes the colon rule below trustworthy.

## The measurements

### The colon-plus-capital tic

Counts of `<lowercase>: <Capital>` against `<lowercase>: <lowercase>`. The
lowercase counts are somewhat inflated by extraction noise (equations, figure
labels), so read the ratio as a signal, not as an exact rate.

| Paper | Tier | colon+Cap | colon+lower | ratio |
| --- | --- | --- | --- | --- |
| `tms_risk` 2025 | 1 | 19 | 2 | **0.90** |
| `trial_to_trial` 2026 | 1 | 20 | 26 | **0.43** |
| `ways_of_linking` 2016 | 3 | 40 | 11 | 0.78 |
| `qsm_gradual` 2014 | 3 | 17 | 7 | 0.71 |
| `subcortical_cocktail` 2015 | 3 | 9 | 4 | 0.69 |
| `numrisk` 2023 | 2 | 3 | 6 | 0.33 |
| `odcs` 2021 | 2 | 9 | 23 | 0.28 |
| `sequential_representations` 2026 | excl. | 13 | 108 | 0.11 |
| `ofc_value` 2026 | excl. | 9 | 64 | 0.12 |
| `neural_priors` 2026 | 2 | 6 | 40 | 0.13 |
| `attend_ignore` 2024 | excl. | 4 | 20 | 0.17 |
| `probability_distortions` 2025 | excl. | 19 | 75 | 0.20 |

The separation between "papers he wrote alone" and "papers he co-authored" is
about as clean as a stylometric marker gets, and it holds back to 2014.

### Connective frequencies (occurrences per 10,000 words)

Tier 1 papers, rounded:

| Marker | `trial_to_trial` | `tms_risk` |
| --- | --- | --- |
| `Thus,` | 8 | 6 |
| `However,` | 6 | 7 |
| `First,` | 4 | 3 |
| `Crucially,` | 3 | 1 |
| `Moreover,` | 3 | 4 |
| `Note that` | 3 | 3 |
| `Finally,` | 3 | 1 |
| `Importantly,` | 1 | 1 |
| `Notably,` | 1 | 1 |
| `Furthermore,` | 1 | 3 |
| `Specifically,` | 0 | 4 |
| `Indeed,` | 1 | 2 |

`Note that` appears at ~3/10k in Tier 1 and also in every Tier 3 paper (3–6
occurrences each) — career-long.

### Sentence length

Medians 12–26 words, means 20–30, 90th percentile ~50 across the whole corpus,
with no meaningful tier difference. He is not a short-sentence writer, and
"tighten this" should not mean "chop every sentence in half".

### Spelling

Journal-imposed, not personal:

| Paper | `modelling`/`modeling` | `behaviour`/`behavior` |
| --- | --- | --- |
| `tms_risk` (preprint, his draft) | 1 / 13 | 0 / 47 |
| `trial_to_trial` (Nat Commun, produced) | 16 / 0 | 48 / 10 |
| `neural_priors` (Nat Commun, accepted, preprint text) | 0 / 2 | 0 / 45 |

Conclusion: he drafts in American English; Nature-family production converts to
British. Don't treat either as the personal style.

### Vocabulary that is distinctively his

Per 10k words, Tier 1 versus the excluded control group: `acuity` 8 vs 0,
`noisy` 8 vs 4, `mechanistic` 5 vs 1. These are load-bearing technical words in
his framework, not stylistic flourishes — which is exactly why they should be
reused verbatim rather than paraphrased.

### Words that are *not* anti-patterns

Checked against the corpus because they are plausible over-corrections:
`elucidate` (7 occurrences), `well-known` (10), `robustly` (9), `novel` (13),
`showcase` (2), `shed light` (4), `dovetail` (2), `underscore` (3) all occur.
Don't prune them.

Genuinely absent from the entire corpus: `delve`, `tapestry`, `myriad`,
`holistic`, `pivotal`, `cutting-edge`, `paradigm shift`, `nuanced`,
`it is well known that`, and exclamation marks in body text.

## Prior art this builds on

`~/git/tms_risk/notes/manuscript_style_card.md` is an earlier, narrower version
of this analysis, extracted from a single manuscript (`TMS_paper_v10.docx`) and
validated in use. Its rules are all preserved here. One apparent conflict is
resolved rather than dropped: the card says to avoid "notably" and "crucially"
because "he uses 'critically' deliberately", while the corpus shows all three in
use at low rates. The reconciled rule is the one in `SKILL.md` — they are all
fine, but only as pointers at the design feature that licenses an inference,
never as filler.

`~/git/tms_risk/notes/PAPER_EDITS.md` and `notes/CHAT_PROMPT.md` are the source
of Rule 0 (never invent a number; name the model when the model is doing the
work; placeholder tokens). That material is epistemic discipline rather than
style, and it is the part of this skill most worth obeying.

## Extending this corpus

When a new first-author paper lands:

1. Extract with `pdftotext -layout` into a scratch directory.
2. Re-run the colon ratio and the connective table against it.
3. Only add a rule if the new paper and at least one existing Tier 1 paper agree.
   A single occurrence is an accident, not a habit.
4. If a rule here is contradicted, update the rule and note the contradiction —
   don't leave both.
