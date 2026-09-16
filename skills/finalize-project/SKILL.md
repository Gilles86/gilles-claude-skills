---
name: finalize-project
description: Make a research project fully reproducible and publicly archived once the paper is accepted or in revision — the ordered finalization checklist with a definition of done per item, language-agnostic (Python, MATLAB, R). Covers the code↔Methods audit (both directions), the paper-result→code map and fresh-clone smoke test, pinned environments + lock files + pinned in-house libraries (e.g. braincoder, bauer, a lab MATLAB toolbox), data sharing on OpenNeuro (staging copy, BIDS validator, defacing with a real QC gate, de-identification audit) and figshare (one tidy behavioural table + codebook), the GitHub→Zenodo code release with DOI, the data/code availability statements, and funder/institutional obligations (SNSF, ERC, UZH, Swiss HRA). Use whenever the user says "paper accepted", "finalize the project", "make this reproducible", "release the code", "share the data", "upload to OpenNeuro", "put the behaviour on figshare", "Zenodo DOI", "deface", "de-identify", "code availability", "data availability", "tag a release", "pin the environment", or asks whether the Methods match the code. Pairs with **data-archival** (institutional backup of the finished project) and **cogneuro-project** (repo layout for Python projects).
---

# Finalizing a project for publication

A paper is accepted (or in the last revision round). The project now has to
survive without you: a stranger with the public data, the public code and the
pinned environment must regenerate every figure and every reported number, and
every sentence in the Methods must describe what the code actually did.

This skill is the **ordered checklist** for the whole lab. Nothing in it
assumes a language: where a command is shown for Python, the MATLAB or R
equivalent is the same idea (the references give both where they differ).
Each item has a *definition of done* and points to a `references/` file with
the how-to. The body is short on purpose; read the reference when you reach
the item.

**Cross-skill pointers** (optional; only if those skills are installed)
- Repo layout and `libs/` pinning for Python projects → **cogneuro-project**
- Backing the finished project up to the cluster + institutional share → **data-archival**
- Running the defacing array / validator on a SLURM cluster → **sciencecluster**
- Which fMRIPrep version ran, from the container path → **fmriprep**

## HARD RULES

- **Never modify the canonical dataset.** Every release operation (gzip,
  header cleaning, renaming, defacing) reads from the canonical tree and writes
  to a staging tree. `SOURCE` is read-only, always.
- **Nothing undefaced, nothing un-audited leaves the machine.** Undefaced
  anatomicals live in a `WORK` dir that is never uploaded; only QC-approved
  defaced images enter the upload tree. A JSON `"Defaced": true` flag proves
  nothing about the pixels.
- **A human looks at every defaced image.** Automated metrics gate; eyes approve.
- **The paper cites what the artifacts say, not what the code says today.**
  Output directory names, logs, `SPM.mat`/trace metadata and lock files record
  what ran; the working tree may have drifted since.
- **Private material never enters the public repo** — `notes/` (reviewer
  correspondence, drafts), API keys, absolute personal paths. Check the
  *history*, not just the tree, before flipping the repo public.
- **No `git commit`/`push`/`tag`/upload without the owner's explicit go.**
  Release steps are irreversible in ways a checkout is not (a DOI is forever).

## Order of work

```
0 obligations ─► 1 freeze results ─► 2 Methods→code audit ─► 3 code→Methods audit ─► 4 pin envs + libs
                                                                        │
      ┌─────────────────────────────────────────────────────────────────┘
      ▼
5 README + result→code map + archive/ + fresh-clone smoke test
      │
      ├─► 6 OpenNeuro (stage → de-identify → deface + QC → validate → upload → snapshot)   ← long pole, start early
      ├─► 7 figshare behavioural table
      ▼
8 GitHub (ruffgroup) + Zenodo release ─► 9 availability statements + cross-link every DOI
```

Items 2–4 can change code and therefore figures, so they come before the
README and the smoke test. Defacing (6) is the long pole (minutes per image +
human QC of every image) and is independent of the code audit — start it as
soon as the dataset scope is decided, in parallel.

## The checklist

### 0. Know the obligations (funder, institution, law)

Read the grant(s) behind the paper and the consent form before deciding
licences, repositories and timing. SNSF: data underlying the publication in
a FAIR, preferably non-commercial repository *at publication*, code archived
(not just GitHub), final DMP, CC BY article without embargo. ERC/Horizon
Europe: trusted repository by project end, CC BY/CC0 data + CC0 metadata,
DMP, EU funding visibility. UZH: ZORA deposit mandate, Open Science Policy
(recommendations). Swiss HRA/HRO: a public dataset must be *anonymised* in
the Art. 25 sense or covered by consent. Primary sources and the concrete
consequences per item: [`references/funder_policies.md`](references/funder_policies.md)

**Done when:** the applicable rows of that table are ticked, the funding
statements and grant numbers are ready for paper + metadata records, and the
consent/protocol wording has been checked against what will be shared.

### 1. Freeze the list of results

Enumerate every figure panel, table, SI figure and every number in the main
text and SI (N, p, r, CI, BIC differences, parameter values). This list is the
spine for items 2, 5 and 9. Store it in `notes/` (gitignored) if it quotes
the manuscript, or directly as the skeleton of the README's result→code table.

**Done when:** a table with one row per result exists, and every row has an
empty "produced by" column waiting to be filled.

### 2. Methods → code audit

Extract every numeric and procedural claim from the Methods (and figure
legends) into a claims table; trace each to `file:line`; record the value the
code *invokes* (job script → command-line flag → script default → constant,
or the `matlabbatch` struct actually run), not the first constant you find;
flag mismatches and triage them (paper wrong / code drifted / ambiguous).
→ [`references/methods_code_audit.md`](references/methods_code_audit.md)

**Done when:** every claim row has a `file:line` and a status, every mismatch
has a resolution (Methods edit listed for the response letter, or a refit
scheduled), and software versions in the Methods come from lock files /
`ver` output / container tags rather than memory.

### 3. Code → Methods audit (reverse)

Walk the entry-point scripts and the data-loading layer (a `Subject` class,
a `load_subject.m`, an R loader — wherever paths, defaults and exclusions
live); list every flag, branch, threshold and constant that changes a result;
check each is in the paper. Typical omissions: run/trial exclusions, dummy
scans, smoothing FWHM, confound set, CV fold construction, voxel-selection
threshold, grid bounds, optimizer settings, noise-model family, seeds, which
fit variant feeds which figure.
→ [`references/methods_code_audit.md`](references/methods_code_audit.md) §Reverse

**Done when:** every result-changing decision in the code is either in the
Methods/SI or on the list of Methods additions.

### 4. Pin environments and in-house libraries

A human-readable environment spec with pinned versions per platform *and
language* (conda/pip `environment.yml`; R `renv.lock`; MATLAB release +
`ver` output + the exact toolbox set on the path) **plus** byte-level lock
exports in `environments/`, taken *on the machine that ran the results*.
Software outside the env (fMRIPrep container tag, FreeSurfer, MRIQC, FSL,
AFNI, SPM revision, CmdStan) in a table. In-house libraries (`braincoder`,
`bauer`, a lab toolbox, …) pinned to the **commit SHA that produced the
published fits** — in the spec, as the submodule/vendored commit, and as a
tag in the library repo. → [`references/environments.md`](references/environments.md)

**Done when:** the environment rebuilds from the spec on a clean machine and
the pinned in-house library resolves to the pinned commit (Python: `import
lib; lib.__file__`; MATLAB: `which lib_function` points into `libs/`; R:
`packageDescription()`), the lock files are committed with their export date,
and the README states which env produced which results.

### 5. Reproducible from the README

Few entry points: one script per figure (Python, MATLAB or R), one script
that prints every reported statistic in manuscript order, a "paper result →
code" table covering every row of item 1, and a stage-by-stage pipeline with
exact commands. Dead and exploratory code goes to `archive/` with a README
table (`git mv`, history preserved). Then the **fresh-clone smoke test**:
clone into a temp dir, build the env from the spec, point at the public data,
run the quick path, and compare the outputs with the published figures /
committed source-data tables.
→ [`references/reproducibility_readme.md`](references/reproducibility_readme.md)

**Done when:** every result row names a script/notebook and its upstream
inputs; the smoke test passes from a fresh clone without touching anything
gitignored; a grep for personal absolute paths (`/Users/`, `/home/`, `C:\`)
over the tracked code is empty (or only in documented defaults); nothing
loads from `archive/` or from another project's folder.

### 6. Neuroimaging data on OpenNeuro

Stage a copy (never edit canonical) → de-identify (headers, filenames,
sidecars, `participants.tsv`, sourcedata) → deface every face-bearing volume
with a QC gate → BIDS-validator-clean → upload private → snapshot → DOI. Include
only the data needed to reproduce the paper; derivatives (if shipped) get their
own `dataset_description.json` with `GeneratedBy` + `SourceDatasets`.
Release code lives in a `data_release/` folder of the repo, one script per
step in whatever language the lab uses (`stage_raw`, `stage_derivatives`,
`deface_subject`, `qc_subject`, `make_qc_report`, `write_metadata`,
`audit_release`, `export_behavior`, plus cluster job wrappers), so every step
is re-runnable per subject and the gates are explicit.
→ [`references/openneuro.md`](references/openneuro.md),
[`references/defacing.md`](references/defacing.md),
[`references/deidentification.md`](references/deidentification.md)

**Done when:** `deno run -A jsr:@bids/validator <staging>` reports zero
errors; every high-res 3D volume in the upload tree is on the QC-approved
list; the identifier audit over the whole tree is clean; a snapshot exists
with a DOI; a few T1w opened in the OpenNeuro viewer are visibly defaced.

### 7. Behavioural data on figshare

One long tidy TSV (one row per trial, all subjects, an `excluded` flag with
reason rather than silently dropped rows) built through the same data-loading
function the analyses call, plus a README codebook. Recompute the paper's
headline behavioural statistics from the exported file alone, in a fresh
session that does not load the project code. Reserve the DOI before writing
the statements; private link for reviewers; publish at acceptance.
→ [`references/figshare.md`](references/figshare.md)

**Done when:** the headline numbers reproduce from the TSV alone; every
column is in the codebook with unit and coding; the DOI is reserved.

### 8. Code on GitHub (`ruffgroup/<project>`) + Zenodo DOI

Repo lives under `github.com/ruffgroup/<project>` (transfer if it was
personal; GitHub redirects the old URL). Pre-public scrub of tree *and*
history, `LICENSE`, `.zenodo.json` + `CITATION.cff`, Zenodo–GitHub
integration switched on **before** tagging, then `v1.0.0` + GitHub release →
Zenodo mints a version DOI and a concept DOI. Tag the library commit in the
library repo too. → [`references/zenodo_release.md`](references/zenodo_release.md)

**Done when:** the Zenodo record exists with correct authors/ORCIDs/licence,
the tagged tree is the one the smoke test passed on, and the README carries
the concept-DOI badge.

### 9. Availability statements + cross-linking

Data Availability (OpenNeuro DOI, figshare DOI, what each contains, what is
*not* shared and why) and Code Availability (GitHub URL, Zenodo DOI, library
DOIs + pinned commits, fMRIPrep/SPM version). Every artifact links to every
other: paper ↔ README ↔ Zenodo `related_identifiers` ↔ OpenNeuro
`ReferencesAndLinks` ↔ figshare description. Templates in
[`references/zenodo_release.md`](references/zenodo_release.md) §Statements.

**Done when:** each DOI appears in every other artifact's metadata, and the
README's top section is the same text as the paper's statements.

## Proposed additions — confirm with the owner before adopting

Items not on the original requirement list. Each is one decision; ask, then
either fold it into the checklist above or drop it.

1. **Licences, explicit:** code MIT (or BSD-3) with a `LICENSE` file; data
   CC0 on OpenNeuro (required there); figshare CC BY 4.0 vs CC0. Say them in
   the README and in the statements.
2. **`CITATION.cff` + `.zenodo.json` in the project repo** (not just the
   libraries) so GitHub shows "Cite this repository" and Zenodo gets the right
   authors/ORCIDs instead of GitHub usernames.
3. **Journal Source Data files:** one workbook/TSV per figure with the plotted
   numbers — the figure scripts should emit these as a by-product (the
   source-data-table cache pattern already does).
4. **Ethics/consent check before upload:** confirm the approved consent form
   permits public sharing of de-identified MRI and demographics; the approval
   number goes into `dataset_description.json` `EthicsApprovals`. Decide
   age binning / sex sharing at the same time.
5. **Git-history scrub:** `git log --all --stat -- notes/ '*.env' '*.key'` and a
   secrets/paths scan over all commits before the repo goes public; if
   anything private was ever committed, rewrite history (`git filter-repo`)
   *before* the Zenodo archive freezes it.
6. **Institutional archive step:** after the release, back the canonical
   dataset, the staging tree's approved outputs, and the fitted derivatives
   up per the **data-archival** skill, and record the release DOIs in the
   private project→archive map.
7. **Random seeds:** every stochastic step (grid init, MCMC, simulations,
   train/test splits, `rng`) seeded and the seed stated in Methods; if a
   result was produced unseeded, say so and report the Monte-Carlo variability.
8. **Figure-diff check as part of the smoke test:** regenerate and compare
   numerically (source-data tables) — not just "it ran".
9. **RRIDs** for fMRIPrep, FreeSurfer, FSL, AFNI, SPM, MATLAB, nilearn, PyMC,
   etc. in the Methods; journals increasingly ask.

## Reference index

| File | What it covers |
|---|---|
| [`funder_policies.md`](references/funder_policies.md) | SNSF / ERC–Horizon Europe / UZH / Swiss HRA obligations with primary-source links, and what each means for the checklist |
| [`methods_code_audit.md`](references/methods_code_audit.md) | Claims table, tracing invoked values, artifact-over-code rule, reverse audit checklist |
| [`reproducibility_readme.md`](references/reproducibility_readme.md) | README structure, entry-point discipline, result→code map, `archive/`, fresh-clone smoke test |
| [`environments.md`](references/environments.md) | Spec + lock per language (conda/pip, renv, MATLAB `ver`), reconstructing pins after the fact, pinning in-house libs, software outside the env |
| [`zenodo_release.md`](references/zenodo_release.md) | GitHub org transfer, pre-public scrub, `.zenodo.json`/`CITATION.cff`, tag → DOI, submodule caveat, statement templates |
| [`openneuro.md`](references/openneuro.md) | Staging, BIDS fixes seen in practice, validator + CLI via deno, private → snapshot → DOI, derivatives scope |
| [`defacing.md`](references/defacing.md) | Which volumes bear faces, WORK/TARGET split, raw-voxel mask application, QC gate metrics + visual report, FreeSurfer allowlist |
| [`deidentification.md`](references/deidentification.md) | Beyond faces: filenames, physio/eyetracking headers, NIfTI text fields, FreeSurfer stamps, logs; whole-tree audit approach |
| [`figshare.md`](references/figshare.md) | One tidy table, codebook, recompute-from-export check, reserve DOI, reviewer link |
| [`identifier_audit.py`](references/identifier_audit.py) | Generic whole-tree identifier scan (Python template; needs only Python + nibabel, nothing project-specific) |
| [`deface_apply_qc.py`](references/deface_apply_qc.py) | Generic mask-apply-at-raw-voxel-level + verify + metrics + MIP report (Python template; usable from any lab) |
