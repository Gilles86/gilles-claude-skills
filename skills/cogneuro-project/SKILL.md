---
name: cogneuro-project
description: Organize a cognitive-neuroscience fMRI project (Gilles's house style) — flat-package layout, Subject class as single source of truth, pipeline-stage submodules, co-located SLURM jobs, multi-env conda, BIDS derivatives discipline, plus conventions for using the in-house braincoder (PRF/encoding) and bauer (Bayesian behavioral) libraries. Use when bootstrapping a new project, refactoring an old one, adding a new analysis stage, or auditing a project for drift from the convention. Triggers on "set up a new project", "where should this script go", "how do I structure...", or working in any of ~/git/{neural_priors, abstract_values, retinonumeral, retsupp, value_capture, tms_risk, risk_experiment, bauer, braincoder}.
---

# Cognitive-neuroscience project organization

The house style for Gilles's fMRI projects, distilled from auditing
neural_priors, abstract_values, retinonumeral, and retsupp. Where the
projects converge, that's the convention. Where they diverge, this
skill picks one — usually the version the newest project (retsupp)
settled on — and flags the others as drift to clean up next time
that file is touched.

When working in an existing project, follow what's already there
unless explicitly refactoring; swapping `slurm_jobs/` ↔ `jobs/`
mid-project just to match this skill is churn for its own sake.

For SLURM internals (conda activation, GPU constraints, NFS dogpile,
log conventions), see the **sciencecluster** skill — this skill says
*where* SLURM scripts live in the repo, sciencecluster says *what's
inside them*. For figure aesthetics, see **scientific-figures**. For
the NIfTI dtype trap and local-vs-cluster split, see global CLAUDE.md.

## Canonical layout

```
<project>/
├── setup.py                 # minimal: find_packages(), package_data=subjects.yml
├── README.md                # paper-facing: science + setup + pipeline
├── CLAUDE.md                # developer-facing: recipes, gotchas, model table
├── .gitignore               # see references/gitignore
├── .gitmodules              # libs/ submodules
├── libs/                    # git submodules (braincoder, bauer, exptools2)
├── create_env/              # conda env builds + sbatch wrappers
│   ├── create_cpu_env.sh
│   ├── create_gpu_env.sh
│   ├── environment_cpu.yml
│   └── environment_cuda.yml
├── environment_apple_silicon.yml   # local mac dev (top-level)
├── environment_psychopy.yml        # optional, experiment-only
├── experiment/              # PsychoPy/exptools2 task code
├── notes/                   # markdown working notes (NOT Jupyter)
│   ├── INDEX.md
│   ├── STATUS.md
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
                             #   (not the BIDS derivatives — those live on
                             #   /shares/zne.uzh/gdehol/ds-<project>
                             #   and /data/ds-<project>)
```

Each pipeline submodule has its own `slurm_jobs/` subdirectory with
matching `.sh` wrappers next to the `.py` scripts.

## Naming standardization

Where projects currently disagree, pick the right column for new code;
leave existing code alone unless refactoring.

| Pick | Avoid | Why |
|------|-------|-----|
| `create_env/` | `cluster_env_setup/` | shorter; retsupp's choice |
| `slurm_jobs/` | `jobs/` | unambiguous |
| `modeling/` | `encoding_model/`, `encoding_models/` | covers PRF + non-PRF encoding + decoding (retsupp) |
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

Skeleton: see [references/subject_class.py](references/subject_class.py).

Six rules:

1. **Constructor: `Subject(subject_id, bids_folder=DEFAULT_LOCAL)`.**
   Accept both `1` and `'01'`; zero-pad internally. Pilots are
   strings (`'pil01'`). Default `bids_folder` is the local mac path
   (`/data/ds-<project>`); SLURM scripts override to the cluster path.
   Never hardcode the cluster path inside `data.py`.

2. **One method per data type, one keyword per BIDS entity.** Stable
   surface area:
   ```python
   sub.get_preprocessed_bold(session, run=None, space='T1w')
   sub.get_single_trial_estimates(session, kind='stim', smoothed=False, roi=None)
   sub.get_prf_parameters_volume(model_label, smoothed=False)   # returns NIfTI dict
   sub.get_prf_parameters_tsv(model_label, smoothed=False)      # returns DataFrame
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
   sessions, run counts, exclusions. Don't hardcode "8 runs"
   anywhere; call `sub.get_runs(session)`. Schema in
   [references/subjects.yml](references/subjects.yml).

5. **Cache the slow stuff at the TSV layer.** PRF parameter NIfTIs are
   big and most downstream code wants one row per voxel.
   `get_prf_parameters_tsv()` reads `derivatives/extracted_pars/*.tsv`;
   the NIfTI variant is only for spatial analyses. neural_priors
   already does this — adopt elsewhere.

6. **Wrap dtype-safe NIfTI writes in `Subject._write_volume()`.**
   ```python
   img = masker.inverse_transform(values)
   img.set_data_dtype(np.float32)
   img.header.set_slope_inter(slope=1, inter=0)
   img.to_filename(path)
   ```
   Without this, the output inherits the (uint8) mask dtype and
   quantizes to ~256 values via `scl_slope`. See global CLAUDE.md
   ("NIfTI dtype trap"). Every project independently bites on this —
   solve once.

**Optional patterns** (use when paradigm warrants):

- **Derivative-name composition from boolean flags** —
  retinonumeral does `encoding_model.cv.smoothed/`. If you adopt this,
  define `_DERIV_FLAG_ORDER = (...)` as a module constant; both the
  writer and reader compose names through the same helper. If your
  flags are simple (one or two booleans), separate methods are
  cleaner.
- **Module-level experimental constants** — retsupp's
  `distractor_locations` / `location_angles` are imported by
  downstream code rather than redefined. Worth doing whenever you
  have geometric constants used across modules.
- **A "master DataFrame" entry point** — retsupp's
  `get_conditionwise_summary_prf_pars(model=8)` returns a long-format
  DataFrame with PRF params × ROI labels × condition pre-joined.
  Worth replicating if your paradigm has conditions.

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

Not every project needs every stage — add as needed, but use the
canonical name.

## Analysis script CLI convention

```python
# <package>/modeling/fit_prf.py
def main(subject, bids_folder='/data/ds-<project>', model=4, smoothed=False):
    print(f'[fit_prf] subject={subject} model={model} '
          f'smoothed={smoothed} bids={bids_folder}', flush=True)

    # Heavy imports inside main() — keeps `python -c "import <pkg>"` fast
    # and avoids GPU init during argparse error paths.
    from <package>.utils.data import Subject

    sub = Subject(subject, bids_folder=bids_folder)
    # ...

if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('subject', type=int)
    p.add_argument('--bids_folder', default='/data/ds-<project>')
    p.add_argument('--model', type=int, default=4)
    p.add_argument('--smoothed', action='store_true')
    args = p.parse_args()
    main(args.subject, bids_folder=args.bids_folder,
         model=args.model, smoothed=args.smoothed)
```

Rules:
- **Positional `subject` (int) first** — never `--subject`.
- **`--bids_folder`** as the only path argument; default to the local
  mac path; SLURM scripts override.
- **One Python script per analysis variant**, but **model variants**
  use `--model <int>` not separate scripts (abstract_values:
  `fit_aprf.py --model session-shift`).
- **Defer heavyweight imports** (`tensorflow`, `jax`, `pymc`) until
  inside `main()`; keeps imports fast and surfaces argparse errors
  before GPU init.
- **Echo the resolved config** at the top of `main()` so SLURM logs
  are searchable and typos surface fast.

Template: [references/script_template.py](references/script_template.py).

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

One `.sh` wraps **one** `.py` script and threads CLI flags through
positional args or `--export`. Naming: `<analysis>[_<variant>].sh`
(e.g., `fit_aprf.sh`, `fit_aprf_cv.sh`). Avoid `submit.sh`, `run.sh`,
`job1.sh`.

The internals (account, conda activation, GPU constraints, log paths,
`--array=1-N%150` throttling, dependency chains) live in the
**sciencecluster** skill — don't duplicate here.

## Environment management

Three conda envs, all defined in `create_env/`:

- `environment_cpu.yml` — cluster CPU + local Linux dev
- `environment_cuda.yml` — cluster GPU jobs (TF + CUDA pinned)
- `environment_apple_silicon.yml` — local mac dev (top-level, since
  it's mac-only)

Optionally `environment_psychopy.yml` at the top level for the
experiment machine — PsychoPy has incompatible deps with the analysis
stack, so isolate.

`create_cpu_env.sh` and `create_gpu_env.sh` are sbatch scripts so the
GPU env builds on a GPU node with the right CUDA toolkit visible.

Templates: [environment_cpu.yml](references/environment_cpu.yml),
[environment_cuda.yml](references/environment_cuda.yml).

## libs/ — braincoder, bauer, exptools2

In-house libraries live both as git submodules under `libs/` and as
pip-installed packages from git URLs in the env YML. Two sources, two
purposes:

- **The env YML pins a commit/branch** for reproducibility. This is
  what runtime imports use:
  ```yaml
  - pip:
    - "braincoder @ git+https://github.com/Gilles86/braincoder.git@keras-backend"
  ```
- **The submodule is for editable development.** After building the
  env, override the pinned install with the submodule:
  ```bash
  conda activate <project>
  pip install -e libs/braincoder
  ```
  Now you can edit `libs/braincoder/braincoder/models.py` and the
  changes show up immediately in the project. To freeze again, drop
  the editable install and let pip pick up the YML's pinned version.

Don't vendor copies. Don't rely on `libs/braincoder` being on
`sys.path` (only works from repo root).

### braincoder — PRF and encoding-model fitting

Backend-agnostic encoding-model library (TensorFlow / JAX / PyTorch
via Keras 3). Used in neural_priors, abstract_values, retsupp,
retinonumeral, value_capture. Lives in `<package>/modeling/`.

Canonical imports and usage pattern:

```python
from braincoder.models import GaussianPRF2DWithHRF, LogGaussianPRF
from braincoder.hrf import SPMHRFModel
from braincoder.optimize import ParameterFitter, ResidualFitter, StimulusFitter
from braincoder.utils import get_rsq
from braincoder.utils.math import get_expected_value, get_sd_posterior
from braincoder.utils.stats import fit_r2_mixture, r2_fdr_threshold

# 1. Build the model
hrf_model = SPMHRFModel(tr=1.6)
model = GaussianPRF2DWithHRF(grid_coordinates=stimulus_grid, hrf_model=hrf_model)

# 2. Fit parameters: grid → gradient descent
fitter = ParameterFitter(model, data=bold, paradigm=stimulus)
grid_pars = fitter.fit_grid(mu_x=mu_x_grid, mu_y=mu_y_grid, sigma=sigma_grid)
pars = fitter.refine_baseline_and_amplitude(grid_pars)
pars = fitter.fit(init_pars=pars, learning_rate=0.05, max_n_iterations=1000)

# 3. Fit noise model (for decoding)
resid_fitter = ResidualFitter(model, data=bold, parameters=pars)
omega, dof = resid_fitter.fit()

# 4. Decode test data into stimulus posterior
stim_fitter = StimulusFitter(data=test_bold, model=model, omega=omega, dof=dof)
posteriors = stim_fitter.fit(stimulus_range=test_stims)

# 5. Summarize
r2 = get_rsq(bold, model.predict(parameters=pars, paradigm=stimulus))
mean_estimate = get_expected_value(posteriors, stimulus_range)
sd_estimate = get_sd_posterior(posteriors, stimulus_range)
```

Three-stage fit (grid → refine baseline/amplitude → full GD) is the
standard recipe across all projects. Don't skip the refine step — it
makes the GD warm-start dramatically better.

Template: [references/braincoder_prf_example.py](references/braincoder_prf_example.py).

### bauer — Bayesian behavioral models

Hierarchical Bayesian models for risky choice, magnitude comparison,
and psychophysics (PyMC backend). Used in risk_experiment, tms_risk.
Lives in `<package>/behavior/`.

Canonical imports and usage pattern:

```python
from bauer.models import (
    RiskModel, RiskLapseModel, LossAversionModel,
    MagnitudeComparisonModel, MagnitudeComparisonLapseModel,
    FlexibleNoiseRiskModel, RiskModelProbabilityDistortion,
    PsychometricModel,
)
from bauer.utils.bayes import get_posterior, summarize_ppc
from bauer.utils.math import softplus_np, inverse_softplus_np

# 1. Format trials as long DataFrame: subject, condition, choice, magnitudes
df = sub.get_behavioral_data()  # via Subject class

# 2. Build + fit model (PyMC NUTS)
model = RiskModel(df, prior_estimate='objective')
trace = model.fit(draws=1000, tune=1000, chains=4, target_accept=0.95)

# 3. Posterior summaries
posterior = get_posterior(trace, model)            # tidy DataFrame
ppc = summarize_ppc(model, trace)                  # posterior predictive

# 4. Save
trace.to_netcdf(out_path / 'trace.nc')
```

Pick the right model class (the fit/parse code is the same):

| Class | Use for |
|-------|---------|
| `RiskModel` | Standard expected-utility risky choice |
| `RiskLapseModel` | Same + lapse rate |
| `LossAversionModel` | Risky choice with separate gain/loss utilities |
| `MagnitudeComparisonModel` | Two-magnitude comparisons (numerosity, line length, etc.) |
| `MagnitudeComparisonLapseModel` | Same + lapse |
| `FlexibleNoiseRiskModel` | Risky choice with magnitude-dependent noise |
| `RiskModelProbabilityDistortion` | Adds Prelec probability weighting |
| `PsychometricModel` | Generic psychometric curve |

Template: [references/bauer_cogmodel_example.py](references/bauer_cogmodel_example.py).

### exptools2 — experiment infrastructure

PsychoPy + ioHub wrapper for trial sequencing and timing. Lives in
`experiment/` (top-level), used at runtime on the experiment machine
only. Don't pull into the analysis env (PsychoPy has incompatible
deps).

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

## CLAUDE.md content checklist

Hand-curated, not auto-generated. Required sections:

1. **One-line pitch** — paradigm, N, scanner
2. **Paths** — local + cluster BIDS roots, sourcedata, derivatives
3. **Subject naming** — pilot vs study, zero-padding, exclusions
4. **Environment setup** — env names, build commands, known
   incomplete envs on cluster
5. **Pipeline stages** in order, with file paths and one-line
   descriptions
6. **CLI examples** — copy-paste-runnable commands for common
   analyses
7. **SLURM examples** — typical array submissions
8. **Per-subject gotchas** — pilot quirks, bugged runs, missing
   sessions

Optional (add as the project grows):
9. **Model label table** — when there are multiple model variants;
   note where the dispatch lives if scattered across scripts
10. **Experimental constants** — TR, volumes per run, stimulus
    geometry (read from per-run yml when possible, don't hardcode)
11. **Subject QC ranking** — when there's variation in fit quality
    that affects exclusion/demo decisions
12. **Plotting conventions** — FWHM vs σ, label conventions, etc.

Skeleton: [references/CLAUDE.md.template](references/CLAUDE.md.template).
retsupp's CLAUDE.md (~300 lines) is the most fleshed-out reference
in the wild.

## Improvements not yet consistently applied

These were absent or partial across the four audited projects.

1. **`tests/test_data.py`** — construct `Subject(1)` and
   `Subject(quirky_id)`, exercise every `get_*` method, and round-trip
   a 64-distinct-value array through `_write_volume` to catch the
   uint8 quantization bug. Doesn't need real BIDS data — mock to a
   tmpdir. None of the four projects have this; all four have
   suffered Subject-class regressions that quietly corrupted
   downstream. See [references/test_data.py](references/test_data.py).

2. **`Subject._write_volume()`** — the dtype-safe NIfTI writer.
   Add to every project's Subject class; remove ad-hoc per-script
   guards.

3. **Ad-hoc one-off scripts in `scripts/one_off/<topic>/`**, not at
   repo root. abstract_values has `fix_sub06_t2mgz.sh`,
   `run_decoding_pil01.sh`, `fix_and_move_bids.py` at the top —
   each should be in `scripts/one_off/<topic>/` with a README naming
   what it fixed and when.

4. **`scripts/ingest_new_session.sh`** orchestrator — chains
   fmriprep → glmsingle → modeling → decoding via
   `--dependency=afterok` per-subject (failure isolation).
   abstract_values has the canonical example. Skeleton:
   [references/ingest_new_session.sh](references/ingest_new_session.sh).

5. **`Makefile` or `tasks.py`** for the 3–4 most common commands
   (env build, BIDS smoke test, one-subject fit). Easier than
   re-deriving the right CLI from CLAUDE.md every time.

6. **A `.gitignore` that actually excludes `build/` and
   `*.egg-info/`** — neural_priors has `build/` committed. Use
   [references/gitignore](references/gitignore).

7. **A "master DataFrame" entry point on Subject** when the paradigm
   has conditions — long-format DF with PRF params × ROI × condition
   pre-joined. retsupp's `get_conditionwise_summary_prf_pars()` is the
   model. Saves dozens of inline merges across plotting scripts.

## Bootstrapping a new project

See [references/README.md](references/README.md) — copy-paste recipe
plus a reference index of every template file.
