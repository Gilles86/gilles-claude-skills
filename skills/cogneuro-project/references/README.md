# cogneuro-project references

Copy-pasteable templates for the conventions in `../SKILL.md`. Each
file uses `<project>` and `<package>` as placeholders — replace before
use. Replace `<task>` in BIDS filenames with the actual BIDS task
label (e.g., `numerosity`, `risk`).

## What's here

| File | Goes to | Purpose |
|------|---------|---------|
| `subject_class.py` | `<package>/utils/data.py` | Subject class skeleton — single source of truth, dtype-safe writes, lazy metadata loader, split TSV/NIfTI getters |
| `subjects.yml` | `<package>/data/subjects.yml` | Per-subject session/run metadata schema |
| `setup.py` | `setup.py` | Minimal pip-editable install |
| `script_template.py` | `<package>/<stage>/<script>.py` | CLI script: positional subject + `--bids_folder`, deferred heavy imports, config echo |
| `braincoder_prf_example.py` | `<package>/modeling/fit_prf.py` | 3-stage PRF fit (grid → refine → GD), noise-model fit, decoding |
| `bauer_cogmodel_example.py` | `<package>/behavior/fit_cogmodel.py` | Bayesian behavioral model fit (PyMC NUTS), posterior + PPC summaries |
| `environment_cpu.yml` | `create_env/environment_cpu.yml` | CPU conda env (local Linux + cluster CPU) |
| `environment_cuda.yml` | `create_env/environment_cuda.yml` | GPU conda env (cluster GPU jobs) |
| `CLAUDE.md.template` | `CLAUDE.md` | Project-level developer guide skeleton |
| `gitignore` | `.gitignore` | Default ignores: build artifacts, logs, NIfTI in derivatives/, secrets |
| `ingest_new_session.sh` | `scripts/ingest_new_session.sh` | Orchestrator: rsync → BIDS → cluster upload → dependency-chained SLURM |
| `test_data.py` | `tests/test_data.py` | Smoke tests for Subject class + dtype guard |

## SLURM templates

For SLURM `.sh` wrapper files (account, conda activation, GPU
constraints, throttling, dependency chains), see the **sciencecluster**
skill's `references/`:

- `array_cpu_template.sh`
- `array_gpu_template.sh`
- `submit_chain.sh`

This skill says **where** they live in the project tree
(`<package>/<stage>/slurm_jobs/`); the sciencecluster skill says
**what's inside them**.

## Quick start: bootstrap a new project

```bash
PROJ=new_thing
SKILLS=~/git/gilles-claude-skills/skills/cogneuro-project/references

mkdir -p ~/git/$PROJ/{$PROJ/{utils,data,prepare,glm,modeling,behavior,visualize,notebooks},notes/{data,figures,analyses,archive},experiment,libs,create_env,scripts,tests}
cd ~/git/$PROJ

git init
git submodule add git@github.com:Gilles86/braincoder.git libs/braincoder
# Add libs/bauer if doing Bayesian behavioral modeling
# Add libs/exptools2 if running PsychoPy experiments

cp $SKILLS/setup.py .
cp $SKILLS/gitignore .gitignore
cp $SKILLS/CLAUDE.md.template CLAUDE.md
cp $SKILLS/subject_class.py $PROJ/utils/data.py
cp $SKILLS/subjects.yml $PROJ/data/subjects.yml
cp $SKILLS/environment_cpu.yml create_env/
cp $SKILLS/environment_cuda.yml create_env/
cp $SKILLS/braincoder_prf_example.py $PROJ/modeling/fit_prf.py
cp $SKILLS/bauer_cogmodel_example.py $PROJ/behavior/fit_cogmodel.py
cp $SKILLS/ingest_new_session.sh scripts/
cp $SKILLS/test_data.py tests/

# Empty __init__.py files
touch $PROJ/__init__.py $PROJ/{utils,prepare,glm,modeling,behavior,visualize}/__init__.py

# Replace placeholders globally (uses sd from your installed CLI tools)
sd '<project>' "$PROJ" $(fd -t f)
sd '<package>' "$PROJ" $(fd -t f)
# Then by hand: <task>, <topic>, <N>, <X>, etc. in CLAUDE.md
```

After this: build the env (`sbatch create_env/create_cpu_env.sh` on
the cluster), `pip install -e .`, optionally
`pip install -e libs/braincoder` for editable braincoder dev. Then
adapt `prepare/`, `cluster_preproc/fmriprep.sh`, and the SLURM
wrappers from an existing similar project (retsupp is the freshest
reference).
