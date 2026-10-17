# Revision checklist

Run this before returning any manuscript text. It is ordered by cost of getting
it wrong, not by how quick it is to check.

---

## 1. Truth (blocking — do not return text that fails these)

- [ ] **Every number traces to an artifact.** No value was rounded, interpolated
      from a figure, or remembered. Anything not sourced is a `⟦TOKEN⟧`.
- [ ] **Every `⟦TOKEN⟧` introduced is listed at the end of the response**, so it
      can be checked against the substitution table.
- [ ] **No number is reported for a fit that has not converged.** Brackets stay,
      no value is written.
- [ ] **Model-derived summaries name their model.** No sentence treats an RNP, a
      slope, a utility parameter or a decoded value as if it had been measured.
- [ ] **Simulated and observed data were summarised identically**, and the prose
      says so where the comparison is made.
- [ ] **No claim is carried by weaker evidence than the sentence implies.** If
      model comparison establishes three things, the text claims three; anything
      carried by posterior predictive checks is attributed to them.
- [ ] **Nothing is claimed to be impossible that merely failed once.** "Does not
      sample reliably under this parameterisation, because X" — not "cannot be
      fitted".

## 2. Argument

- [ ] Every Results subsection heading is a **declarative claim with a full
      predicate**, not a topic label.
- [ ] Every rhetorical question in the Introduction is **answered by a Results
      subsection**, in the same order.
- [ ] Each Results subsection states the **prediction before the number**.
- [ ] Each Results subsection **closes with a flagged summary** (`In sum,`,
      `In summary,`, `Thus,`, `Taking stock,`).
- [ ] The Introduction ends with the **triple**: "Here, we…", roadmap, preview.
- [ ] Every obvious reviewer objection has a **paragraph that concedes it before
      answering it**. Model complexity, stimulus generality, Bayesian
      flexibility, and correlational-vs-causal are the recurring four.
- [ ] Future work names a **design** — manipulation, measure, paradigm — not a
      need for more research.
- [ ] The Discussion's reach ladder has **real referents** (a clinical
      population, a named practice), not a gesture at importance.

## 3. Voice

- [ ] **Colons are followed by a capital letter** where they unpack a claim, and
      the colon — not the em dash — is doing the explanatory work.
- [ ] **Em dashes** appear only for the appositive definition of the central
      construct, typically in the abstract's first sentence.
- [ ] `Crucially` / `Critically` / `Importantly` / `Notably` each point at a
      design feature that licenses an inference. **Delete any that survive
      deletion with no loss.** Budget: 2–3 per section.
- [ ] `Note that …` is used for technical caveats a careless reader would miss —
      roughly three per paper, not per section.
- [ ] Reasoning is **enumerated inline in prose**. No bullet lists in Results or
      Discussion.
- [ ] **No mid-paragraph bold**, no exclamation marks.
- [ ] Everyday instantiations come **in threes**.
- [ ] Sentences were not uniformly shortened. Median 18–26 words is correct;
      a 50-word sentence that resolves is fine.

## 4. Hedging asymmetry

- [ ] **No credible result is hedged.** Search for `suggests`, `may`, `might`,
      `appears` attached to a statistic and remove them.
- [ ] **No interpretation is stated flatly.** Every mechanistic claim beyond the
      data carries a hedge or an explicit scope qualifier.
- [ ] The headline claim is confident; its qualifier is precise. ("can be rooted
      in", "at least partly", "at least in the small-stake laboratory experiments
      widely used in the field".)
- [ ] Nothing is said to be *proven*.

## 5. Terminology

- [ ] **One name per construct, throughout.** Grep the draft for the near-synonym
      set (noise / imprecision / variability / unreliability; acuity / precision
      / fidelity) and confirm each word is used for exactly one quantity.
- [ ] Every abbreviation is defined at first use **in each of** abstract,
      introduction and methods.
- [ ] External models are attributed by author on first mention, then abbreviated.
- [ ] Spelling convention (British or American) is consistent across the whole
      document and matches the existing draft.

## 6. Statistics

- [ ] **Every effect size has an interval.** No bare `r`, `t`, `d` or
      difference-in-means.
- [ ] Bayesian quantities are written `pBayesian`, identified as **one-sided
      posterior probabilities**, with the multiple-comparison status stated.
- [ ] Model comparison reports **ELPD and the difference in standard-error
      units**, plus a stacking weight where available.
- [ ] A result that exists for two sessions or scanners is reported for **both**.
- [ ] Recovery / reliability checks appear in the Results with numbers.

## 7. Figure captions

- [ ] Title is a claim.
- [ ] `n` is stated.
- [ ] **The caption says what the error bands are** — this is the one that gets
      forgotten.
- [ ] Every reference line, colour mapping and glyph is defined.
- [ ] Test, sidedness and correction status are given, including a reason when no
      correction was applied.
- [ ] Schematic panels declare that they show no data.
- [ ] Model-derived axes are named as such.

## 8. Delivery

- [ ] Edits are **before/after replacements of existing sentences**, not fresh
      paragraphs dropped in.
- [ ] Returned **section by section with a short note on what changed** — not a
      diff, not a wall of text.
- [ ] No signposting was added that the draft does not already use.
- [ ] Sections the user said to leave alone were left alone.
