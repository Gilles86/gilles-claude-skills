---
name: cogneuro-project
description: Organize a cognitive-neuroscience fMRI project (Gilles's house style) — flat-package layout, Subject class as single source of truth, pipeline-stage submodules, co-located SLURM jobs, multi-env conda, BIDS derivatives discipline, plus conventions for using the in-house braincoder (PRF/encoding) and bauer (Bayesian behavioral) libraries. Use when bootstrapping a new project, refactoring an old one, adding a new analysis stage, or auditing a project for drift from the convention. Triggers on "set up a new project", "where should this script go", "how do I structure...", or working in any of ~/git/{neural_priors, abstract_values, retinonumeral, retsupp, value_capture, tms_risk, risk_experiment, bauer, braincoder}.
---

# Cognitive-neuroscience project organization

The house style for Gilles's fMRI projects, distilled from auditing
neural_priors, abstract_values, retinonumeral, retsupp, tms_risk.
Where the projects converge, that's the convention. Where they
diverge, this skill picks one — usually the version the newest
project settled on — and flags the others as drift to clean up next
time that file is touched.

When working in an existing project, follow what's already there
unless explicitly refactoring; swapping `slurm_jobs/` ↔ `jobs/`
mid-project just to match this skill is churn for its own sake.

**Cross-skill pointers:**
- SLURM internals (conda, GPU, NFS, log conventions) → **sciencecluster**
- fmriprep operational gotchas → **fmriprep**
- Figure aesthetics → **scientific-figures**
- NIfTI dtype trap, local-vs-cluster split → global CLAUDE.md

**`references/` are real exemplars.** Most files are verbatim or
lightly-excerpted code from working projects (`abstract_values`,
`tms_risk`), each with a provenance header naming source path and git
SHA. Treat them as concrete reference, not blank-fill templates. The
genuinely synthetic templates that remain (`subjects.yml`, `gitignore`,
`CLAUDE.md.template`, `setup.py`, `README.md`) are marked as such.

## Canonical layout

```
<project>/
├── setup.py                 # minimal: find_packages(), package_data=subjects.yml
├── README.md                # paper-facing: science + setup + pipeline
├── CLAUDE.md                # developer-facing: recipes, gotchas, model table
├── .gitignore               # see references/gitignore
├── .gitmodules              # libs/ submodules
├── libs/                    # git submodules (braincoder, bauer, exptools2)
├── environment_cuda.yml     # cluster GPU env (or environment_linux.yml,
│                            #   or inside create_env/ if it needs sbatch build)
├── environment_apple_silicon.yml   # local mac dev
├── environment_psychopy.yml        # optional, experiment-only
├── experiment/              # PsychoPy/exptools2 task code
├── notes/                   # markdown working notes (NOT Jupyter)
│   ├── INDEX.md  STATUS.md
│   ├── data/                # small TSVs aggregated from cluster
│   ├── figures/             # generated PDFs/PNGs
│   ├── analyses/            # focused per-analysis writeups
│   └── archive/             # superseded outputs
├── scripts/                 # orchestrators, one-offs (NOT at repo root)
├── tests/                   # pytest — at minimum, test_data.py
├── <project>/               # main package; same name as project dir
│   ├── __init__.py
│   ├── data/subjects.yml    # per-subject session/run metadata
│   ├── utils/data.py        # Subject class — SINGLE SOURCE OF TRUTH
│   ├── prepare/             # raw → BIDS, events files
│   ├── cluster_preproc/     # fmriprep wrapper, bids_filter.json
│   ├── nordic/              # NORDIC denoising (7T only)
│   ├── preprocess/          # confound regression, mean ts
│   ├── glm/                 # GLMsingle single-trial betas
│   ├── modeling/            # PRF / encoding-model fits + decoding
│   ├── surface/             # FreeSurfer surface projection
│   ├── visualize/           # plotting helpers
│   ├── behavior/            # behavioral parsing + Bayesian models (bauer)
│   └── notebooks/           # exploratory Jupyter (inside the package)
└── derivatives/             # OPTIONAL: small version-controlled outputs only
                             #   (not BIDS derivatives — those live on
                             #   /shares/zne.uzh/gdehol/ds-<project>
                             #   and /data/ds-<project>)
```

Each pipeline submodule has its own `slurm_jobs/` subdirectory with
matching `.sh` wrappers next to the `.py` scripts.

## Naming standardization

Pick the right column for new code; leave existing code alone unless
refactoring.

| Pick | Avoid | Why |
|------|-------|-----|
| `create_env/` | `cluster_env_setup/` | shorter; retsupp's choice |
| `slurm_jobs/` | `jobs/` | unambiguous |
| `modeling/` | `encoding_model/`, `encoding_models/` | covers PRF + non-PRF encoding + decoding |
| `behavior/` | `cogmodels/` | what abstract_values and retsupp use |
| `notes/` (markdown) | `notebooks/` (Jupyter) for docs | markdown is durable; .ipynb diffs are noise |
| `<project>/notebooks/` | top-level `notebooks/` | keep notebooks importable from the package |
| `scripts/<one_off>.sh` | `<one_off>.sh` at repo root | abstract_values has 4 ad-hoc scripts at root — a mess |

**`--bids_folder` vs `--bids-folder`**: argparse handles both
identically with `dest='bids_folder'`. Most existing code uses
underscore — match it.

## The Subject class — single source of truth

Every project has `<package>/utils/data.py` with a `Subject` class.
This is the **only** place that knows about disk paths, BIDS file
naming, per-subject quirks, and derivative caching. Analysis scripts
import `Subject`; they do NOT build paths themselves.

Real exemplar: [references/subject_class.py](references/subject_class.py)
(abstract_values). Six conventions:

1. **Constructor: `Subject(subject_id, bids_folder=DEFAULT)`.** Accept
   both `1` and `'01'`; zero-pad internally. Pilots are strings
   (`'pil01'`). Default `bids_folder` is the local mac path
   (`/data/ds-<project>`); SLURM scripts override to the cluster path.
   Never hardcode the cluster path inside `data.py`.

2. **One method per data type, one keyword per BIDS entity.**
   ```python
   sub.get_preprocessed_bold(session, run=None, space='T1w')
   sub.get_single_trial_estimates(session, kind='stim', smoothed=False, roi=None)
   sub.get_prf_parameters_volume(model_label, smoothed=False)   # NIfTI dict
   sub.get_prf_parameters_tsv(model_label, smoothed=False)      # DataFrame
   sub.get_brain_mask(session=None, return_masker=True)
   sub.get_volume_mask(roi, session=1, return_masker=False)
   sub.get_confounds(session, kind='minimum')
   sub.get_onsets(session, run=None)
   sub.get_behavioral_data(session=None, tasks=None)
   ```
   Don't return "either a DataFrame or a NIfTI dict" from one method —
   split them. Don't shadow the builtin `type`; use `kind`.

3. **Encapsulate per-subject quirks here, never in scripts.** retsupp
   branches on `subject_id < 3` (early sourcedata layout); retinonumeral
   has a pulse-t0 fix for sub-06 ses-2 run-5. These belong in
   `Subject._apply_*_quirks()` with a comment naming the quirk. Add a
   pytest case for each quirky path so regressions surface.

4. **Read per-subject metadata from `<package>/data/subjects.yml`** —
   sessions, run counts, exclusions. Don't hardcode "8 runs" anywhere;
   call `sub.get_runs(session)`. Schema:
   [references/subjects.yml](references/subjects.yml).

5. **Cache the slow stuff at the TSV layer.** PRF parameter NIfTIs are
   big and most downstream code wants one row per voxel.
   `get_prf_parameters_tsv()` reads `derivatives/extracted_pars/*.tsv`;
   the NIfTI variant is only for spatial analyses. neural_priors does
   this — adopt elsewhere.

6. **Wrap dtype-safe NIfTI writes in `Subject._write_volume()`.**
   ```python
   img = masker.inverse_transform(values)
   img.set_data_dtype(np.float32)
   img.header.set_slope_inter(slope=1, inter=0)
   img.to_filename(path)
   ```
   Without this, output inherits the (uint8) mask dtype and quantizes
   to ~256 values via `scl_slope`. See global CLAUDE.md ("NIfTI dtype
   trap"). Every project bites on this independently — solve once.

Optional patterns (derivative-name composition from boolean flags,
module-level experimental constants, master-DataFrame entry point):
[references/subject_class_patterns.md](references/subject_class_patterns.md).

## Submodules by pipeline stage

| Submodule | Inputs | Outputs |
|-----------|--------|---------|
| `prepare/` | DICOM, behavior TSVs | BIDS dataset |
| `nordic/` | BIDS func | denoised func (7T only) |
| `cluster_preproc/` | BIDS | `derivatives/fmriprep/` |
| `preprocess/` | fmriprep BOLD | `derivatives/cleaned/` |
| `glm/` | cleaned BOLD | `derivatives/glmsingle/` |
| `modeling/` | single-trial betas | `derivatives/prf*/` |
| `surface/` | parameter NIfTIs | `.func.gii` files |
| `visualize/` | summary TSVs | PDFs in `notes/figures/` |
| `behavior/` | events TSVs | bauer/HSSM trace files |

Not every project needs every stage — add as needed, use the canonical
name. For the `surface/` projection recipe (nilearn `vol_to_surf` with
pial+white sampling → `SurfaceTransform` for fsaverage, pycortex
`blend_curvature` viewer): [references/surface_sampling.md](references/surface_sampling.md).

## Analysis script CLI convention

Real exemplar: [references/analysis_script_example.py](references/analysis_script_example.py)
(abstract_values `fit_glmsingle.py`). Rules:

- **Positional `subject` (int or `'pil01'`) first** — never `--subject`.
- **`--bids_folder`** as the only path argument; default to the local
  mac path; SLURM scripts override.
- **One Python script per analysis variant**, but **model variants** use
  `--model <label>` not separate scripts (abstract_values:
  `fit_aprf.py --model session-shift`).
- **Defer heavyweight imports** (`tensorflow`, `jax`, `pymc`,
  `glmsingle`) until inside `main()` — keeps `import <project>` fast
  and surfaces argparse errors before GPU init.
- **Echo the resolved config** at the top of `main()` so SLURM logs are
  searchable and typos surface fast.
- **Hard-fail loudly on incomplete subjects**
  (`sub.require_complete_sessions()`) with `--allow-incomplete` as the
  explicit escape hatch. Silent multi-session aggregation downstream
  is much worse than an early crash.

## SLURM jobs co-located with Python modules

```
modeling/
├── fit_prf.py
├── decode.py
└── slurm_jobs/
    ├── fit_prf.sh
    ├── fit_prf_smoothed.sh
    └── decode.sh
```

One `.sh` wraps **one** `.py` script. Inputs go via `--export key=value`,
not positional args. Naming: `<analysis>[_<variant>].sh` (e.g.,
`fit_aprf.sh`, `fit_aprf_cv.sh`). Avoid `submit.sh`, `run.sh`, `job1.sh`.

Real exemplar: [references/slurm_job_example.sh](references/slurm_job_example.sh)
— shows the `--export` pattern, dynamic `ARGS=(...)` array,
`PYTHONUNBUFFERED=1` + direct env binary, log redirection.

The internals (account, conda activation, GPU constraints, log paths,
`%150` throttling, dependency chains) live in the **sciencecluster**
skill — don't duplicate here.

## libs/ — braincoder, bauer, exptools2

In-house libraries live both as git submodules under `libs/` and as
pip-installed packages from git URLs in the env YML.

- **The env YML pins a commit/branch** for reproducibility. This is
  what runtime imports use:
  ```yaml
  - pip:
    - "braincoder @ git+https://github.com/Gilles86/braincoder.git@keras-backend"
  ```
- **The submodule is for editable development.** After building the
  env, override the pinned install:
  ```bash
  conda activate <project>
  pip install -e libs/braincoder
  ```
  Edits to `libs/braincoder/braincoder/models.py` show up immediately.
  Drop the editable install to freeze again.

Don't vendor copies. Don't rely on `libs/braincoder` being on
`sys.path` (only works from repo root).

The three libraries:

- **braincoder** — PRF / encoding-model fitting (Keras 3
  multi-backend). Lives in `<package>/modeling/`. Real fit example:
  [references/braincoder_prf_example.py](references/braincoder_prf_example.py)
  shows the canonical 3-stage fit (`fit_grid` →
  `refine_baseline_and_amplitude` → `fit`). **Never skip the refine
  step** — it makes gradient-descent warm-start dramatically better.
- **bauer** — Bayesian behavioral models (PyMC / numpyro). Lives in
  `<package>/behavior/`. Real fit example with model dispatch +
  DDM/RDM handling:
  [references/bauer_cogmodel_example.py](references/bauer_cogmodel_example.py).
- **exptools2** — PsychoPy + ioHub experiment runtime. Lives in
  `experiment/` (top-level), used on the experiment machine only.
  Don't pull into the analysis env (PsychoPy has incompatible deps).

## notes/ for markdown, not notebooks

The single best refinement from retsupp:

- `notes/INDEX.md` — manually curated list of every doc in `notes/`
- `notes/STATUS.md` — what's done, in progress, blocked
- `notes/<topic>.md` — focused writeups (one per analysis decision)
- `notes/analyses/<analysis>/` — per-analysis subfolders
- `notes/data/` — TSVs aggregated on the cluster, rsync'd back for
  local plotting (cf. global CLAUDE.md)
- `notes/figures/` — generated PDFs/PNGs (gitignore the regenerable
  scratch ones, commit the paper-figure outputs)
- `notes/archive/` — superseded analyses, kept for provenance

Notebooks still belong in the project, but **inside the package** at
`<package>/notebooks/`. Top-level `notebooks/` makes
`from <project> import utils` brittle.

## Reference index

Load on demand. Most are real-code excerpts (see provenance headers).

**Code exemplars**
- `subject_class.py` — Subject class (abstract_values)
- `analysis_script_example.py` — analysis script (abstract_values fit_glmsingle.py)
- `slurm_job_example.sh` — SLURM .sh wrapper (abstract_values)
- `braincoder_prf_example.py` — braincoder 3-stage fit (abstract_values fit_aprf.py)
- `bauer_cogmodel_example.py` — bauer model dispatch (tms_risk fit_model.py)
- `ingest_new_session.sh` — pipeline orchestrator (abstract_values)
- `test_data.py` — Subject pytest suite (tms_risk)
- `environment_cuda.yml` — cluster CUDA stack (abstract_values environment_linux.yml)
- `environment_apple_silicon.yml` — Mac M-series, optional metal GPU

**Deeper conventions** (load when needed)
- `envs.md` — when to split into 2 / 3 / 4 envs; canonical TF/Keras/JAX stack
- `subject_class_patterns.md` — optional Subject patterns
  (deriv-name composition, module constants, master-DataFrame entry)
- `surface_sampling.md` — volume → fsnative → fsaverage projection recipe
- `claude_md_checklist.md` — what to put in a project's CLAUDE.md
- `audit_punchlist.md` — house-style gaps to clean up when touching a project

**Synthetic templates** (copy and edit)
- `CLAUDE.md.template` — starting CLAUDE.md
- `subjects.yml` — per-subject metadata schema
- `gitignore` — sensible default
- `setup.py` — minimal `find_packages()`
- `README.md` — bootstrap recipe for a new project
