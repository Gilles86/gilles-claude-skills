# Behavioural data on figshare

One tidy long table, one codebook, one DOI. The table is *exactly* what the
paper analysed — built through the same data-loading function the analysis
scripts call, in whatever language — so anyone can recompute the behavioural
results without the imaging data or the project code.

## Files

```
<project>_behavior.tsv          # one row per trial, all subjects, all sessions
README.md                       # codebook + design + exclusions + how to load
participants.tsv                # optional; same IDs as OpenNeuro; age/sex only if shared there too
```

One long table beats per-subject files: `read_csv` / `readtable` /
`read.delim` on one file and go. Per-subject files are fine as an extra, not
as the primary.

### Table rules

- **Identifiers match OpenNeuro**: `subject` = `01`, `02`, … (or `sub-01`),
  `session`, `run`, `trial_nr`.
- **One row per trial**, one column per variable, no wide blocks, no
  MultiIndex, no derived columns that a reader could not recompute from the
  others unless the paper reports them (then include *and* document the
  formula).
- **Exclusions as data**: keep excluded trials/subjects in the table with an
  `excluded` boolean and `exclusion_reason` string, rather than dropping
  them. The reader can then reproduce the exclusion, not just its result.
- **Units in the codebook, not the column name**: `rt` in seconds documented,
  not `rt_ms`/`rt_s` mixtures.
- **Missing values as `n/a`** (BIDS convention), never empty strings or `-1`.
- **Types**: booleans as `True/False` or `0/1` — consistently; integers as
  integers (`Int64`, not `1.0`).
- **No absolute timestamps**; onsets relative to run start only.
- **Condition labels as words** (`narrow`/`wide`), not the internal code.

### Build script

`data_release/export_behavior.{py,m,R}`: loops over the released subjects
(same list as the OpenNeuro release), calls the analysis's own loader,
renames columns to TSV-friendly names (`log(risky/safe)` → `log_risky_safe`),
casts types, selects the documented columns **from a single column list**,
writes the TSV, and writes the codebook from descriptions keyed by that same
list (a Python dict, a MATLAB table/struct array, an R data frame) — so the
codebook cannot silently lag the table.

## Codebook `README.md`

- Paper title, authors, DOI/preprint; links to OpenNeuro dataset and GitHub
  repo (add the Zenodo DOI when it exists).
- Design in one paragraph: N, sessions × runs × trials, conditions, what a
  trial is.
- Exclusions: which subjects/trials and why, and how they are marked.
- **Column table**: `column | type | unit | values/coding | description`.
- How to load, one line each:
  `pandas.read_csv(f, sep='\t', na_values='n/a')`;
  `readtable(f, 'FileType','text', 'Delimiter','\t', 'TreatAsMissing','n/a')`;
  `read.delim(f, na.strings='n/a')` — and a three-line example that
  reproduces one headline number.
- Licence (CC BY 4.0 default on figshare; CC0 if you prefer no attribution
  requirement — decide once, same for the paper's statement).

## The recompute check

In a **fresh session that does not load the project code** (no `import`, no
`addpath`, no `library(<project>)`), from the exported TSV alone, recompute the paper's headline behavioural statistics
(the group means, the t-test, the correlation the abstract quotes). They must
match the manuscript to reporting precision. If they don't, the table is
missing a column or an exclusion — fix the table, not the check.

## figshare mechanics

1. Create item → type **Dataset**; title = paper title + "— behavioural data";
   description = the README's first two paragraphs plus the links.
2. Upload files. Keep `README.md` as a separate file *and* paste its
   essentials into the description (figshare renders the description; the
   file may go unread).
3. Categories, keywords, licence.
4. **Reserve DOI** (button under the DOI field) — before publishing — and
   put it into the paper's Data Availability and the project README.
5. **Generate private link** for reviewers/editors; the item stays private.
6. **Publish** at acceptance. Later fixes create a new version under the same
   DOI (`…v2`); the reserved DOI resolves to the latest.

Institutional figshare portals (if your university has one) work the same
and count toward institutional data policies; use it if it exists.

## What is *not* shared here

Say it in the README: eye-tracking, physiology, raw task logs, anything with
a date header — either on OpenNeuro after de-identification, or not at all
with a reason.
