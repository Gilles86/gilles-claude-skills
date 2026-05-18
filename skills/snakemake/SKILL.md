---
name: snakemake
description: Practical Snakemake-on-SLURM knowledge — driver placement, rule-output conventions, monitoring, recovery from crashes. Use this skill whenever the user is working with Snakemake (Snakefile, snakemake CLI, snakemake-executor-plugin-slurm), debugging a pipeline that uses Snakemake to orchestrate cluster jobs, or asking how to monitor / restart / recover a Snakemake run on a SLURM cluster. Pairs with the `sciencecluster` skill (general SLURM operational knowledge); this one is the Snakemake-specific overlay.
---

# Snakemake on SLURM — operational knowledge

Grounded in real-incident debugging on a UZH-sciencecluster-like setup
(snakemake 9.x + `snakemake-executor-plugin-slurm`). Some details are
cluster-specific; per-user config (account name, login alias, env
paths) stays in the user's private global config / per-project
CLAUDE.md.

Per-project `Snakefile` lives in the repo (e.g.,
`<project>/snakemake/Snakefile`); generic patterns and recovery
procedures live here.

## Driver placement: in sbatch, NOT on the login node

The Snakemake driver process is a long-running Python program that
keeps a Timer thread per in-flight tracked job. With `jobs: 150` and
default polling, the driver easily holds 100+ threads. Login nodes
typically have `ulimit -u` capped at a few hundred (UZH sciencecluster:
**256** at the time of writing). The driver crashes mid-run with
`RuntimeError: can't start new thread`.

**Fix: run the driver itself as a SLURM job.** Compute nodes have
ulimits in the hundreds of thousands. A 2-CPU / 8GB / 24h slot is
plenty for a 1000-job pipeline.

Template — `<project>/snakemake/run_driver.sh`:

```bash
#!/bin/bash
#SBATCH --job-name=<project>_snake_driver
#SBATCH --account=<account>
#SBATCH --partition=lowprio       # or standard with --qos=medium for >24h
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=1-00:00:00         # see "QoS walltime caps" below
#SBATCH --output=$HOME/git/<project>/<project>/snakemake/logs/driver_%j.log

set -eo pipefail
cd "$HOME/git/<project>"
source "$HOME/data/miniforge3/etc/profile.d/conda.sh"
conda activate <project>_snake

exec snakemake \
    --snakefile <project>/snakemake/Snakefile \
    --workflow-profile <project>/snakemake/profile \
    --configfile <project>/snakemake/config.yaml \
    --rerun-incomplete
```

Submit via:

```bash
ssh <cluster> 'cd ~/git/<project> && sbatch <project>/snakemake/run_driver.sh'
```

## QoS walltime caps (sciencecluster-style)

Many clusters tie partition × QoS to max walltime. UZH sciencecluster:

| QoS | Max walltime | Notes |
| --- | ------------ | ----- |
| normal | 1-00:00:00 | only QoS allowed on `lowprio` |
| medium | 2-00:00:00 | `standard` partition |
| long   | 7-00:00:00 | `standard`, MaxJobsPU=24 |
| debug  | 4 min      | priority 1 |

Submitting `--time=2-00:00:00` on `lowprio` returns
**`Invalid qos specification`** with no further detail. Fix is to
either drop to 1 day (lowprio) or switch partition + qos.

If a 24h driver runs out: Snakemake's persistence layer
(`.snakemake/`) means a resubmit of the same driver picks up where
it left off — losing only the dispatch state (jobs that were in
flight may have completed by the time the new driver starts).

## Rule outputs must be true per-wildcard files

Snakemake enforces: **all output paths of a rule must contain the
same wildcards**. If a tool writes to a shared scratch location
indexed by something OTHER than a rule wildcard (e.g., neuropythy
writing to `freesurfer/<sub>/mri/` regardless of which PRF model
sourced it), you have two options:

1. **Sentinel file** (last resort). Write a small marker file at
   `output: f"{shared_dir}/_done_{wildcards.model}.touch"`. Cheap to
   implement but Snakemake's existence check is then disconnected
   from real output files — manual deletion of the real output
   doesn't trigger rerun.

2. **Per-wildcard archive** (preferred). Have the upstream tool
   *copy* its output to a per-wildcard path after running, and use
   that copy as the rule output. neuropythy's
   `register_retinotopy.py` does this:
   `derivatives/neuropythy/model{N}/sub-XX/{mri,surf}/inferred_*.mgz`.
   Pass the wildcard through to the script
   (`--model {wildcards.model}`) so the per-model copy lands in the
   right place.

If a Snakemake agent or earlier dev built sentinel-based rules, audit
the upstream tool — there's often a real per-model output already
being produced that wasn't being used.

## `rerun-triggers`: drop `mtime` to stop chain cascades

Default `rerun-triggers` includes `mtime`. With a serial chain
`m1 → m2 → ... → m6`, regenerating m1's archive makes m2 rerun
(m1 is "newer than m2 output"), which makes m3 rerun, etc.,
even if m2..m6 archives already exist on disk.

**Set in your workflow profile** (`profile/config.yaml`):

```yaml
rerun-triggers:
  - input    # rule reruns only if the SET of input paths changes
# DON'T include mtime, params, or code unless you really mean it
```

Existence-of-output check still prevents redoing completed rules
through the regular DAG resolution. This narrowly disables the
forward-cascade behaviour only.

## Recovery from a crashed driver

When the driver crashes (or is `scancel`'d) mid-run, some rules
may have partial output files. Snakemake refuses to start the next
invocation with `IncompleteFilesException` listing the files.

**Just add `--rerun-incomplete`** to the next driver invocation —
Snakemake will redo those rules. This should be baked into
`run_driver.sh` so re-submissions just work.

Alternative if `--rerun-incomplete` rebuilds too much: `snakemake
--cleanup-metadata <files>` marks specific outputs as
metadata-clean without touching the file contents. Useful when you
know the file is fine but Snakemake's metadata says otherwise.

## Monitoring: jobs have UUIDs, comments have meaning

The `snakemake-executor-plugin-slurm` hardcodes `--job-name
<run-uuid>` for SLURM bookkeeping (so it can use
`squeue --name <uuid>` for status polls). You cannot override per
rule — `slurm_extra` doesn't accept `--job-name`. But the plugin
also sets `--comment rule_<rule_name>_wildcards_<wildcards>`, which
DOES carry the rule + wildcard.

**Read the comment field**:

```bash
squeue -u $USER -h -O "JobID:14,State:10,TimeUsed:10,Comment:80"
```

A `status.sh` helper that parses the comment into per-rule counts
is in `<project>/snakemake/status.sh` (look at retsupp's for a
template). Pair it with a `tail -f` on the latest
`driver_<jobid>.log` for a "live feed" experience.

For deeper inspection while the driver is running:

- `snakemake --summary` — text table of every target's
  done/missing/incomplete state. Reads on-disk `.snakemake/`
  persistence, doesn't disturb the live driver.
- `.snakemake/log/<run-id>.snakemake.log` — full driver log
  (more verbose than the captured stdout).
- `--rulegraph` and `--dag` — static structural views
  (need graphviz `dot` to render; can be piped to stdout as
  `.dot` text and rendered locally).

## `slurm_extra` is restricted

Plugin owns: `--job-name`, `--output`, `--export`, `--comment`,
`--partition`, `--account`, `--gres`, `--constraint`, `--mem`,
`--cpus-per-task`, `--time`. Setting any of these via
`resources.slurm_extra` raises `WorkflowError` — and the error gets
swallowed by the thread pool, so the symptom is "Submitting N
ready jobs" followed by silent inaction.

If you need one of these per-rule, use the plugin's first-class
keys:

```python
resources:
    slurm_partition="lowprio",
    slurm_account="zne.uzh",
    runtime=60,                # → --time
    mem_mb=24000,              # → --mem
    cpus_per_task=16,          # → --cpus-per-task
    # For GPUs:
    # slurm_extra="--gres=gpu:1 --constraint=L4",  # NO — use:
    gres="gpu:1",
    constraint="L4",
```

Only put truly free-form flags in `slurm_extra` (e.g., a custom
`--qos=foo` for cluster-specific quirks).

## `jobs:` cap and polling rate

`jobs:` caps concurrent SLURM jobs in flight. A few interacting
factors:

- **Cluster's per-user job ceiling.** Above some N the cluster
  starts queuing inside SLURM rather than running concurrently.
- **NFS dogpile**. Submitting a huge array burst (1000+ in seconds)
  triggers `user env retrieval failed requeued held` on some
  clusters. Cap at ~150 to avoid.
- **Driver thread count**. Each tracked job spawns Timer
  threads for polling. At 150 jobs + default 10s polling, login
  nodes with `ulimit -u 256` crash. Compute-node drivers are fine
  to 500+.

Reasonable defaults for the lowprio + sciencecluster style cluster:

```yaml
jobs: 150
seconds-between-status-checks: 30     # default 10 is fine on compute nodes
max-status-checks-per-second: 1
```

## See also (cross-references)

- **`sciencecluster` skill** — general SLURM operational knowledge,
  the cuInit race + flock pattern, `--account=zne.uzh`,
  `--partition=lowprio`, conda activation inside SLURM, NFS dogpile.
  Snakemake inherits these via the driver's `sbatch` submission;
  per-rule SLURM resources in the Snakefile reuse the same
  conventions.
- **Per-project Snakefile** — `<repo>/<project>/snakemake/`
  typically has Snakefile + profile/ + config.yaml + run_driver.sh
  + status.sh. The skill provides patterns; the project's files
  encode the specific DAG.

## TODOs (populate as the migration matures)

- [ ] Skill-side patterns for handling project-specific config
  variants (e.g., the `af_variants` list in retsupp — generated
  rules from a parse-time loop, since wildcards can't pair).
- [ ] Snakemake group jobs for tightly-coupled chunked work (e.g.,
  PRF chunks → merge). Avoids the SLURM submission overhead for
  micro-tasks.
- [ ] Profile-side `--immediate-submit` mode for very large DAGs
  (submit everything up front with `--dependency=afterok:` and let
  SLURM scheduler do the orchestration).
- [ ] Recipes for resuming after `scancel <driver>` mid-flight
  — what survives in `.snakemake/`, what doesn't.
- [ ] Real numbers on driver-side thread accumulation vs `jobs:`
  cap, so we can confidently raise the cap on compute-node drivers.
