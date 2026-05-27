---
name: snakemake
description: Practical Snakemake-on-SLURM knowledge — driver placement, rule-output conventions, monitoring, recovery from crashes. Use this skill whenever the user is working with Snakemake (Snakefile, snakemake CLI, snakemake-executor-plugin-slurm), debugging a pipeline that uses Snakemake to orchestrate cluster jobs, or asking how to monitor / restart / recover a Snakemake run on a SLURM cluster. Pairs with the `sciencecluster` skill (general SLURM operational knowledge); this one is the Snakemake-specific overlay.
---

# Snakemake on SLURM — operational knowledge

Grounded in real-incident debugging on a UZH-sciencecluster-like
setup (snakemake 9.x + `snakemake-executor-plugin-slurm`). Per-user
config (account name, login alias, env paths) stays in private global
config / per-project CLAUDE.md. Per-project `Snakefile` lives in the
repo (e.g., `<project>/snakemake/Snakefile`); generic patterns and
recovery procedures live here.

**Short on purpose.** Three always-true rules (driver placement,
per-wildcard outputs, env-inheritance gotcha) plus the config you set
once. Symptom-specific playbooks (recovery from crash, mtime
cascades, `slurm_extra` error, `Invalid qos`, opaque squeue names)
live in `references/` and load on demand.

## 1. Driver placement: in sbatch, NOT on the login node

The Snakemake driver is a long-running Python program that keeps a
Timer thread per in-flight tracked job. With `jobs: 150` + default
polling, the driver easily holds 100+ threads. Login nodes typically
cap `ulimit -u` at a few hundred (UZH sciencecluster: **256**). The
driver crashes mid-run with `RuntimeError: can't start new thread`.

**Fix: run the driver as its own SLURM job.** Compute nodes have
ulimits in the hundreds of thousands. A 2-CPU / 8 GB / 24 h slot is
plenty for a 1000-job pipeline.

Real template: [`references/run_driver.sh`](references/run_driver.sh)
— `cd` to the repo, conda-activate, unlock+`--rerun-incomplete`
pre-flight, then `exec snakemake`. Submit via:

```bash
ssh <cluster> 'cd ~/git/<project> && sbatch <project>/snakemake/run_driver.sh'
```

Walltime caps are partition × QoS dependent — see
[`references/qos_walltime.md`](references/qos_walltime.md) if you
hit `Invalid qos specification` or want to know what `--time` is
allowed. (Short answer: `lowprio` is 1 day; `standard` + `medium` is
2 days; `standard` + `long` is 7 days. Drivers usually fit in 1 day
and resume cleanly via `.snakemake/` persistence.)

## 2. Rule outputs must be true per-wildcard files

Snakemake enforces: all output paths of a rule must contain the same
wildcards. If a tool writes to a shared scratch location indexed by
something OTHER than a rule wildcard (e.g., neuropythy writing to
`freesurfer/<sub>/mri/` regardless of which PRF model sourced it),
you have two options:

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

## 3. Env inheritance: Snakemake's submitter env is cleaner than yours

Hand-`sbatch`'d scripts inherit `MODULEPATH`, `PATH`,
`LD_LIBRARY_PATH` from the login shell that submitted them.
`snakemake-executor-plugin-slurm` submits with a much cleaner env, so
env-dependent scripts that "work by hand" can break the moment
Snakemake submits the same script.

Classic case: `source /etc/profile.d/lmod.sh` defines `module` but
leaves `MODULEPATH` empty — `module load <X>` then fails with
`module(s) are unknown`. Fix is `source /etc/profile` (whole chain)
or shebang `#!/bin/bash -l`. See the **sciencecluster** skill's
`references/script_shell_setup.md` for the full story.

**When a rule running an existing sbatch script fails fast on the
compute node, suspect this class first** — diff env between a
hand-sbatched run and a Snakemake-submitted run before touching rule
resources or plugin config.

## 4. `jobs:` cap and polling rate — set once

`jobs:` caps concurrent SLURM jobs in flight. A few interacting
factors:

- **Cluster's per-user job ceiling.** Above some N the cluster queues
  inside SLURM rather than running concurrently.
- **NFS dogpile.** Submitting a huge array burst (1000+ in seconds)
  triggers `user env retrieval failed requeued held` on some
  clusters. Cap at ~150 to avoid.
- **Driver thread count.** Each tracked job spawns Timer threads. At
  150 jobs + default 10 s polling, login nodes with `ulimit -u 256`
  crash. Compute-node drivers are fine to 500+.

Reasonable defaults for a sciencecluster-style cluster (in
`profile/config.yaml`):

```yaml
jobs: 150
seconds-between-status-checks: 30     # default 10 is fine on compute nodes
max-status-checks-per-second: 1
rerun-triggers: [input]                # avoid mtime-driven chain cascades
```

That last line matters; see
[`references/rerun_triggers.md`](references/rerun_triggers.md) for
why default `rerun-triggers: [mtime, input, params, code]` causes
forward-cascade reruns of a serial chain.

Real profile config: [`references/profile_config.yaml`](references/profile_config.yaml).

## Templates

Drop-in starting points under `references/` — substitute `<project>`,
`<account>`, `<cluster>` placeholders, tweak per-rule resources:

| File | Purpose |
| --- | --- |
| `references/run_driver.sh` | Driver sbatch wrapper with the unlock + `--rerun-incomplete` pre-flight baked in |
| `references/profile_config.yaml` | Workflow profile (executor: slurm, jobs cap, rerun-triggers, default resources) |
| `references/Snakefile.example` | Minimal Snakefile showing wildcard_constraints, load-time guards, fan-out, real per-wildcard outputs |
| `references/status.sh` | Status helper with `--snake` flag that auto-detects this project's driver UUID |

Don't copy blindly — read the comments. Resource specs in particular
need to match each rule's actual cost (and the cluster's QoS caps).

## Reference index

Load on demand — each is one symptom or one design decision.

- [`qos_walltime.md`](references/qos_walltime.md) — `Invalid qos
  specification`; what `--time` is allowed where; why a 24h driver
  re-submit is safe
- [`driver_recovery.md`](references/driver_recovery.md) — `LockException`
  vs `IncompleteFilesException` after `scancel`; `--cleanup-metadata`
  escape hatch
- [`rerun_triggers.md`](references/rerun_triggers.md) — why dropping
  `mtime` from `rerun-triggers` stops forward-cascade reruns
- [`monitoring.md`](references/monitoring.md) — opaque UUID job names
  + `Comment` field; `--summary`, `--rulegraph`
- [`slurm_extra.md`](references/slurm_extra.md) — plugin-owned flags
  vs first-class resource keys; the silent-inaction failure mode

## See also

- **`sciencecluster` skill** — general SLURM operational knowledge
  (cuInit/flock, conda activation, NFS dogpile). Snakemake inherits
  these via the driver's `sbatch` submission; per-rule SLURM
  resources reuse the same conventions.
- **Per-project Snakefile** — `<repo>/<project>/snakemake/` typically
  has Snakefile + profile/ + config.yaml + run_driver.sh + status.sh.
