---
name: sciencecluster
description: SLURM cluster (UZH sciencecluster) operational knowledge — submitting jobs, conda activation in SLURM context, GPU constraints, log conventions, common failure modes (NFS dogpile, cuInit race, partition contention), and cluster-only vs local code paths. Use this skill whenever the user is working with sciencecluster, SLURM (sbatch, squeue, scontrol, sacct), conda envs on the cluster, GPU jobs with `--gres`, the user mentions "the cluster", or the working directory contains a `slurm_jobs/` folder. Also use for diagnosing held / failed / zombie SLURM jobs.
---

# UZH sciencecluster — SLURM operational knowledge

Generic operational knowledge for the UZH sciencecluster. Per-user
config (SLURM account name, login alias, conda paths, project-specific
env names) lives in the user's private global config — this skill
uses placeholders like `<account>` and `<env>` where applicable.

The cluster login is typically reached via an SSH alias the user
sets up (`ssh sciencecluster`). Jobs run via SLURM; you cannot run
compute on the login node. Always `git pull` before submitting jobs.

## Conda activation in SLURM scripts

SLURM scripts run in whatever shebang they specify (default `#!/bin/bash`,
not the user's interactive zsh). The login `~/.zshrc` is NOT loaded.

**Preferred pattern in SLURM scripts:**

```bash
source "<path-to-miniforge>/etc/profile.d/conda.sh"
conda activate <env>
```

(The user-specific path to miniforge / conda base lives in their
private config — typically `$HOME/data/miniforge3` on this cluster.)

The alternative `. $HOME/init_conda.sh && conda activate <env>` works
on login nodes but has occasionally failed inside SLURM jobs (unclear
cause — possibly compute-node env diff, NFS lag, or interaction with
`set -e`). **Source `conda.sh` directly in SLURM scripts** — fewer
indirections, works the same on login + compute nodes.

For one-shot script runs, prefer the direct env binary (no activation
needed): `<conda-envs-dir>/<env>/bin/python script.py`. Typically the
cluster's envs live under `$HOME/data/conda/envs/`.

## Never use `conda run` in SLURM scripts

`conda run -n env python` pipes stdout through a subprocess, causing
log output to buffer heavily even with `python -u`. Always use the
direct path to the env's python binary, or activate then call python:

```bash
# Good — direct binary, instant log output
export PYTHONUNBUFFERED=1
<conda-envs-dir>/<env>/bin/python -u script.py

# Also fine — activate then call python
source "<path-to-miniforge>/etc/profile.d/conda.sh"
conda activate <env>
export PYTHONUNBUFFERED=1
python -u script.py

# Bad — extra subprocess pipe causes buffered/delayed log output
conda run -n <env> python -u script.py
```

Always set `PYTHONUNBUFFERED=1` in SLURM scripts. No downside in
batch/non-interactive contexts.

## Don't use `set -u` in SLURM scripts that source conda

Conda's per-env activation scripts (e.g.
`activate-binutils_linux-64.sh`) reference variables like `$ADDR2LINE`,
`$AR`, `$AS`, `$CC` that may be unset before activation. Under `set -u`,
sourcing `conda.sh` or `conda activate <env>` aborts on "unbound
variable", killing the job in <5 seconds with a cryptic single-line
log. Symptom in sacct: `FAILED 1:0` with `Elapsed=00:00:02`.

Use `set -eo pipefail` (drop the `-u`) or skip strict mode entirely.

```bash
# Bad — kills the job before python even starts
set -euo pipefail
source "$HOME/data/miniforge3/etc/profile.d/conda.sh"
conda activate <env>

# Fine
set -eo pipefail
source "$HOME/data/miniforge3/etc/profile.d/conda.sh"
conda activate <env>
```

## Log convention: `~/logs/`

SLURM scripts should redirect stdout/stderr to a job-named file under
`~/logs/<jobname>_<jobid>.txt` rather than relying on `slurm-<id>.out`
clutter in the working directory:

```bash
#SBATCH --output=/dev/null

LOGFILE="$HOME/logs/${SLURM_JOB_NAME:-job}_${SLURM_JOB_ID}.txt"
mkdir -p "$(dirname "$LOGFILE")"
exec >"$LOGFILE" 2>&1
```

`~/logs/` becomes the canonical place to tail running jobs:

```bash
tail -f ~/logs/<name>*
ls -t ~/logs/ | head
```

## SLURM job-name convention

Always set an informative `--job-name`. Encode *what* + key parameters
(analysis name, model index, subject id). Generic names like `prf_gpu`
are useless when the queue scrolls. Examples: `prf_m1_sub-02`,
`prf_merge_m1`, `glmsingle_sub-08`.

For array jobs whose name can't be set at submit time, rename
in-script once env vars are known:

```bash
scontrol update jobid="${SLURM_JOB_ID}" \
    name="prf_m${MODEL}_sub-$(printf %02d $SLURM_ARRAY_TASK_ID)"
```

**Caveat:** SLURM's `JobName` field is array-shared — whichever task
calls `scontrol update` last wins the displayed name for ALL sibling
tasks. So don't try to bake the array task index (e.g. chunk_idx)
into the name; it would mislead in squeue. The task index is always
visible in the `_N` suffix of the JobID column anyway.

## Throttle large SLURM arrays — `ArrayTaskThrottle` semantics

Large arrays (~100+ tasks) launched all at once dogpile NFS reading
each task's `$HOME/.bashrc` / `~/.zshrc`. Some tasks fail with
`user env retrieval failed requeued held` and don't auto-retry —
they sit held until you release them. The fix is to **throttle
concurrent tasks** at submit time:

```bash
sbatch --array=1-200%50 ...    # at most 50 of the 200 tasks run at once
```

Or retroactively on an already-submitted array:

```bash
scontrol update jobid=<ARRAY_JOB_ID> ArrayTaskThrottle=50
```

**Important: `ArrayTaskThrottle=N` caps concurrent *running* tasks,
not just dispatch rate.** With %50, at most 50 of an array's tasks
run in parallel; the rest stay PD until a slot frees. Costs some
wallclock if you have more CPUs than the cap, but it's the only knob
SLURM exposes to limit task starts.

Sensible defaults:
- `%50` — mild throttle, good for arrays of ~50-500 tasks. Stops the
  worst dogpile waves.
- `%150` — looser, only useful for very large arrays (1000+) when you
  want most-but-not-all running concurrently.
- No throttle — for arrays under ~30 tasks the dogpile risk is low.

**Across many parallel arrays the dogpile is global** (NFS reads from
`$HOME` regardless of which array). Per-array throttling mitigates
but doesn't eliminate. If you keep seeing held tasks even with
throttles, batch your `sbatch` calls with `sleep 30` between them.

Bulk recovery for held tasks:

```bash
squeue --me -h -t PD --format='%i %r' \
  | awk '/user env/ {print $1}' \
  | xargs -I {} scontrol release {}
```

## Zombie cleanup (DependencyNeverSatisfied)

When an upstream task fails, downstream `afterok` jobs become
permanent zombies. They don't dispatch and don't auto-clean. Find
and cancel them:

```bash
zombies=$(squeue --me -h -t PD --format='%i %r' \
            | grep DependencyNeverSatisfied \
            | awk '{print $1}' \
            | awk -F_ '{print $1}' \
            | sort -u)
[ -n "$zombies" ] && scancel $zombies
```

## Reuse one SSH connection (multiplexing)

Cluster SSH rate-limits new connections — many fresh `ssh
<cluster-alias> '...'` calls in a row get blocked. Multiplexing reuses
one persistent connection, kinder on the shared login cap.

One-time `~/.ssh/config` (replace `<cluster-alias>` with the user's
alias name):

```
Host <cluster-alias>
    ControlMaster auto
    ControlPath ~/.ssh/cm/%r@%h:%p
    ControlPersist 60m
```

`mkdir -p ~/.ssh/cm`. Tear down with `ssh -O exit <cluster-alias>`.

## Never run computationally heavy work on the login node

The login node is shared across all cluster users. Even one-off
"diagnostic" scripts that import nilearn / TF / load large NIfTIs are
heavy enough to slow other people's `ls` and `squeue`, hog memory,
and risk an admin-side kill.

**Pull the data local and run on your laptop** is the preferred path
for diagnostics:

```bash
rsync <cluster-alias>:<remote-path> <local-mirror-path>
# Then run the diagnostic in the local conda env
```

If the data is too big or lives only on cluster filesystems, use
`srun --pty` for an interactive compute-node shell, or wrap in a
quick `sbatch --time=00:10:00` job. Only pure stat queries
(`squeue`, `sacct`, `ls`, `wc -l`, `head`, `git pull`) belong on the
login node.

## Sync code to the cluster via git, NOT rsync

When new code (fit scripts, analysis modules, SLURM wrappers) needs
to be on the cluster, do it via git: commit locally, push to the
remote, then `git pull` on the cluster. **Do not rsync individual
files into the cluster's repo working tree.** Rsync skips the commit
history, breaks the "always git pull before submitting" invariant,
and silently misplaces files when paths don't match perfectly.

If the cluster has uncommitted work in its working tree (it often
does — job scripts get tweaked there), `git stash` before pulling,
then `git stash pop` after. Don't try to merge by hand. Commit any
new files locally first.

Workflow:

```bash
# local
git add path/to/new_script.py path/to/new_job.sh
git commit -m "Add ..."
git push

# cluster
ssh <cluster-alias> 'cd ~/git/<project> && git stash && git pull && git stash pop'
```

## GPU jobs

No special partition required. Request a GPU with `--gres=gpu:1`.
Sciencecluster compute nodes can fail with `module: command not
found` — lmod isn't always set up. In practice, conda envs that
bundle their own CUDA runtime (`jax[cuda12]`, `tensorflow-gpu`
wheels) work without `module load`, since SLURM sets
`CUDA_VISIBLE_DEVICES` from the `--gres` allocation and the bundled
CUDA libs handle the rest. If a custom env DOESN'T bundle CUDA, try
sourcing lmod first (`source /etc/profile.d/lmod.sh`) before module
commands.

```bash
#SBATCH --gres=gpu:1
# No `module load` needed — jax[cuda12] / tensorflow-gpu bundle their own CUDA.
source "<path-to-miniforge>/etc/profile.d/conda.sh"
conda activate <cuda-env>
nvidia-smi               # sanity check
```

GPU fitting only works with a CUDA-built conda env. A standard CPU
env silently falls back to CPU. **Build the CUDA env on a GPU compute
node, not the login node** — the install verifies driver compatibility
at install time.

Verify GPU is visible inside a job before long fits:

```bash
python -c "import jax; print('backend:', jax.default_backend()); print('devs:', jax.devices())"
# or for TF:
python -c "import tensorflow as tf; print(tf.config.list_physical_devices('GPU'))"
```

### GPU constraint syntax

`#SBATCH --constraint="L4|V100|A100"` accepts any of those GPU types.
Useful when L4 alone gives long queue waits. **Exclude H100/H200 if
the env is on CUDA 11.x** (sm_90 needs CUDA 12).

### cuInit race on multi-GPU nodes

When 8 jobs land simultaneously on the same 8-GPU node, parallel
`cuInit` calls deadlock the NVIDIA driver → TF falls back to CPU
→ 60× slowdown → walltime timeouts. Defuse with a 30-second
random startup stagger in the script body:

```bash
sleep $(( RANDOM % 30 ))
```

Pair with `ArrayTaskThrottle` and the stagger is bulletproof.

## Walltime: keep it tight

SLURM's fair-share scheduler prioritizes jobs with **tight walltime
requests**. A 24h walltime makes the job wait longer than a 30-min
walltime, even if both end up running 10 min. Set `--time` close to
the actual expected runtime (with ~2× safety margin if you're not
sure):

```bash
#SBATCH --time=00:25:00   # tight — for known ~10-15 min tasks
```

Run `sacct --format=JobID,JobName,Elapsed | grep <jobname>` on past
runs to calibrate.

## Editing external library packages (vendored / submodule libs)

When patching submodule / vendored library code, treat the package
as an external API — keep comments and docstrings focused on the
contract (what the function does, what it raises, type signatures).
Don't write paragraphs explaining "this used to silently return NaN"
or "before commit ABC123, ..." inside docstrings. That belongs in
the **commit message** — `git log` / `git blame` keep it
discoverable for anyone who wants the incident context without
polluting the API surface for unrelated users of the library.

In your own project code (the application repo), short "why"
comments referencing a specific past pathology are fine, because the
audience IS the project team — but only when removing them would
genuinely confuse a future reader.

## Long runs: always provide a visible progress signal

Whenever you launch something that takes longer than ~1 minute on
the cluster (model fitting, simulations, big preprocessing, batch
jobs), make sure progress is visible — either live in a tail-able
log file or via a built-in progress bar (`pm.sample(progressbar=True)`,
`tqdm`, etc.) with `python -u` + `PYTHONUNBUFFERED=1` so updates
flush promptly. If absolutely nothing is available, print a periodic
flushed status line.
