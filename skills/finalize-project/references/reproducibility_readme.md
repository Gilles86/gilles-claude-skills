# Reproducible from the README

The test is a stranger, not you: given the README, the public data and the
pinned environment, can they regenerate every figure and every reported number
without asking a question? Everything below serves that test, in whatever
language the project is written.

## Two layouts that work

- **One README** with a *pipeline* section (stage-by-stage commands) and a
  *"From paper result to code"* table. Fine when the pipeline is linear.
- **README (concepts) + `REPRODUCE.md` (operational recipe)**. Better when the
  README has grown a long "the model" narrative that would bury the commands.
  The README then opens with a one-paragraph pointer to `REPRODUCE.md`.

Either way, the **first screen** of the README is the availability block:
data DOIs, code DOI, preprocessing version, env spec names, pinned library
commits. That block is the same text as the paper's statements.

## Sections, in order

1. **Title, authors, paper DOI/preprint link.**
2. **Data & software availability** (the block above).
3. **Installation**: `git clone --recursive`, how to build the environment
   (`conda env create -f …` / `renv::restore()` / MATLAB release +
   `setup_paths.m`), how to install the project code and the pinned in-house
   library, and the one verification line that shows the library resolves
   to the pinned commit (see `environments.md`).
4. **Data**: where to download, the expected on-disk layout (`derivatives/`
   tree with one line per stage), which subjects are excluded and why, how
   the data root is configured (a `--bids_folder` flag, a `config.m`, an env
   var), and the single data-loading layer (a `Subject` class, a
   `load_subject.m`, an R loader) that is the only place building paths.
5. **Pipeline stages** in execution order; each stage = purpose, exact command
   (local *and* cluster form), inputs, outputs. Mark stages that are
   *provenance only* (raw → BIDS; the released dataset is already converted).
6. **From paper result to code** — the table (below).
7. **Model labels** (if models are numbered): label → paper name → constraint.
8. **Reproducibility notes**: which fit variant feeds which figure, inclusion
   rules, working directories scripts must be run from, seeds, date-stamped
   outputs, anything that bit you.
9. **Archived code** — one paragraph pointing at `archive/README.md`.
10. **Citation** (BibTeX) and **License**.

## The result → code table

One row per item on the frozen results list (SKILL.md item 1): every main
figure panel, every SI figure, every table, every statistic in the text.

| Paper result | Produced by | Upstream inputs |
|---|---|---|
| Fig. 3a–f | `figures/figure3.m` | group parameter table (stage 5) |
| Decoding statistics (Results §3) | `analysis/decoding_stats.R` (prints a "MANUSCRIPT STATS" block) | stage 6 |
| Fig. S8 | `simulations/simulate_data.py` + `notebooks/recovery.ipynb` § "Fig S8" | model-3 fits |
| Participant demographics (Methods) | `analysis/participant_info.R` | `participants.tsv` |

Rules: name the *section* inside a notebook or live script, not just the
file; say which variant of a script (flag, config) the paper used; mark
**manual** panels explicitly (schematics, brain renders assembled by hand) so
nobody hunts for a script that does not exist.

## Entry-point discipline

Aim for: **one script per figure**, **one script for all reported
statistics**, and a numbered stage per pipeline step. Fewer, longer, boring.

- `figures/figure_0N_<name>.{py,m,R}` writes the panel(s) as vector PDF at
  final physical size into a fixed output dir, and caches the plotted numbers
  as a **source-data table** (TSV/CSV) next to it. Re-styling reads the cache;
  a `--recompute` flag (or `recompute = true`) rebuilds it from
  traces/derivatives. The tables double as the journal's Source Data files.
- `figures/report_statistics.{py,m,R}` prints every number in the main text
  **in manuscript reading order**, as copy-paste-ready strings in the journal's
  format, and writes `reported_statistics.{md,csv}`. Keep Bayesian tail
  probabilities labelled distinctly from frequentist p; note that the third
  decimal of an MCMC p carries Monte-Carlo noise.
- A figure verifier that checks exported PDFs against the journal's artwork
  rules (width, min font size, fonts embedded as text, RGB) pays for itself
  at proof stage.
- Notebooks (Jupyter, MATLAB Live Scripts, Rmd/Quarto) are acceptable entry
  points *if* they run top-to-bottom non-interactively; the smoke test must
  execute them (`jupyter nbconvert --to notebook --execute`,
  `matlab -batch "run('fig3.mlx')"`, `Rscript -e 'rmarkdown::render("fig3.Rmd")'`).
  A notebook that needs cells run out of order is not an entry point — port
  it to a script.
- Never load code from another project (`from other_project import …`,
  `addpath('../other_project')`, `source("../other_project/utils.R")`); it
  works on your machine only. Grep for it.

## `archive/` for dead and exploratory code

Code that produced no result in the paper moves to `archive/` with its
sub-path preserved (`git mv analysis/pupil archive/analysis/pupil`) — history
stays reachable via `git log --follow`. `archive/README.md` is a table:

| Folder | Contents | Why archived |
|---|---|---|
| `figures/` | `figure2/3/4.ipynb` | original-submission figure notebooks, superseded by `…` |

Before moving anything: `grep -rn "<name>" --include='*.py' --include='*.m'
--include='*.R' --include='*.ipynb' .` to confirm nothing loads it; after
moving: the code still loads and the quick figure path still runs. Leave
harmless unused *branches* inside core fit scripts alone — editing the file
that produced the fits risks the reproduction for no gain; note them in the
archive README instead.

## Fresh-clone smoke test

Do this on a machine (or at least a directory and env) that has never seen
the project:

```bash
tmp=$(mktemp -d) && cd "$tmp"
git clone --recursive https://github.com/ruffgroup/<project>.git && cd <project>
# build the env from the spec — one of:
conda env create -f environment.yml && conda activate <env>
Rscript -e 'renv::restore()'
matlab -batch "setup_paths; which -all <lib_entry_function>"     # pinned toolbox resolves, once
# point at the public data (a downloaded OpenNeuro snapshot, or at least one subject)
export BIDS_FOLDER=/path/to/ds00XXXX          # or the project's config file / flag
# the quick path: figures from published derivatives, then the statistics
python figures/figure_01_….py      |  matlab -batch "figure_01"  |  Rscript figures/figure_01.R
python figures/report_statistics.py
```

Then **compare**, don't just run:

- Diff the freshly written source-data tables against the committed ones
  (pandas `assert_frame_equal` with a tolerance; MATLAB `max(abs(a-b),[],'all')`;
  R `all.equal`), or a checksum if deterministic.
- Open the regenerated PDFs next to the published figures.
- Every number `report_statistics` prints matches the manuscript.

Static checks that belong in the same session:

```bash
# personal absolute paths (Unix and Windows)
grep -rnE '/Users/|/home/|/shares/|/data/ds-|[A-Z]:\\\\' --include='*.py' --include='*.m' --include='*.R' --include='*.ipynb' .
# code loaded from another project
grep -rnE 'from (tms_risk|risk_experiment|other_project)|addpath\(.*\.\./|source\(.*\.\./' --include='*.py' --include='*.m' --include='*.R' .
# reads from a gitignored dir
grep -rn 'notes/' --include='*.py' --include='*.m' --include='*.R' --include='*.ipynb' .
# what the clone will NOT have
git status --ignored | grep -vE '^!! (build|.*egg-info|__pycache__|renv/library)'
```

A default data root pointing at a local convention (`/data/ds-<project>`) is
acceptable *if documented*; a hard-coded path inside a function is not.

## Small things that make the difference

- State where scripts must be run from (`cd figures/` relative paths; MATLAB
  scripts that `cd` internally).
- Date-stamped outputs (MCMC run folders) — say how to regenerate and which
  one the paper used.
- If a script needs the cluster (GPU, 100 GB RAM, a MATLAB licence pool), say
  so and provide the reduced local variant or the cached intermediate.
- Every command in the README is copy-pasteable as written: no `<placeholders>`
  left in commands the user is expected to run verbatim, except paths.
