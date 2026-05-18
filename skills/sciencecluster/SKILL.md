---
name: sciencecluster
description: SLURM cluster (UZH sciencecluster) operational knowledge — submitting jobs, conda activation in SLURM context, GPU constraints, log conventions, common failure modes (NFS dogpile, cuInit race, partition contention), and cluster-only vs local code paths. Use this skill whenever the user is working with sciencecluster, SLURM (sbatch, squeue, scontrol, sacct), conda envs on the cluster, GPU jobs with `--gres`, the user mentions "the cluster", or the working directory contains a `slurm_jobs/` folder. Also use for diagnosing held / failed / zombie SLURM jobs.
---

# UZH sciencecluster — SLURM operational knowledge

Generic operational knowledge for the UZH sciencecluster. Per-user
config (SLURM account name, login alias, conda paths, project-specific
env names) lives in the user's private global config — this skill
uses placeholders like `<account>` and `<env>` where applicable.

**Templates:** copy-pasteable SLURM scaffolding lives in
`references/`:

- `array_cpu_template.sh` — CPU array job (stagger + logging + conda activation)
- `array_gpu_template.sh` — same, plus `--gres=gpu:1`, GPU constraint, cuInit-race defense
- `submit_chain.sh` — orchestrator that wires per-subject `afterok` chains

Treat these as starting points; edit the placeholders (`<account>`,
`<env>`, `<path-to-miniforge>`) before submitting.

The cluster login is typically reached via an SSH alias the user
sets up (`ssh sciencecluster`). Jobs run via SLURM; you cannot run
compute on the login node. Always `git pull` before submitting jobs.

## Conda in SLURM scripts

SLURM batch scripts don't source `~/.zshrc` or `~/.bashrc`. Activate
conda by sourcing `conda.sh` directly, or skip activation and use the
env's python binary:

```bash
# Good — activate then call python
source "<path-to-miniforge>/etc/profile.d/conda.sh"
conda activate <env>
export PYTHONUNBUFFERED=1
python -u script.py

# Also good — direct env binary, no activation
export PYTHONUNBUFFERED=1
<conda-envs-dir>/<env>/bin/python -u script.py
```

Three rules:

- **Always `PYTHONUNBUFFERED=1`** — no downside in batch contexts; logs flush promptly.
- **Never `conda run -n <env> python`** — the subprocess pipe buffers
  stdout even with `python -u`.
- **Don't `set -u`** — conda's per-env activation scripts reference unset
  vars like `$ADDR2LINE`, `$AR`, `$CC` and abort under strict mode. Job
  fails in <5 s with `FAILED 1:0`, `Elapsed=00:00:02`. Use `set -eo pipefail`.

The alternative `. $HOME/init_conda.sh && conda activate <env>` has
occasionally failed inside SLURM jobs (unclear cause). Source `conda.sh`
directly — fewer indirections, works the same on login + compute nodes.

## `module` in SLURM scripts: use `#!/bin/bash -l`

Plain `#!/bin/bash` SLURM scripts run as non-login non-interactive
bash and source nothing — `module` isn't defined, `MODULEPATH` is
empty. Use `#!/bin/bash -l` to make the script a login shell so
`/etc/profile` → `/etc/profile.d/*.sh` get sourced and `module`
works:

```bash
#!/bin/bash -l
module load apptainer
```

The silent variant of this bug: a `#!/bin/bash` script that does
`. "$HOME/.bashrc"` thinking that fixes it. `.bashrc` starts with the
standard `case $- in *i*) ;; *) return ;; esac` guard and returns
early non-interactively — its body never runs, and downstream
`module load X` fails. Without `set -e` the script keeps going and
the missing tool fails later as `command not found`. This pattern
sabotaged a lot of old scripts.

`source /etc/profile` works too (explicit; same chain). Don't
`source /etc/profile.d/lmod.sh` alone — it defines `module` but
leaves `MODULEPATH` empty.

## Containers: apptainer, not singularity

Cluster migrated **singularityce → apptainer/1.4.1** (open-source
fork; same CLI, different module name). `.sif` images at
`/shares/zne.uzh/containers/` are unchanged.

```bash
#!/bin/bash -l
module load apptainer
apptainer exec --cleanenv --writable-tmpfs \
    --bind "$CONFIG_FILE:/flywheel/v0/input/config.json" \
    --bind "$OUTPUT_DIR:/flywheel/v0/output" \
    "$SIF_IMAGE" /flywheel/v0/run
```

Symptoms of stale scripts: `Lmod ... module(s) are unknown:
"singularityce"`, or `singularity: command not found` (the
`singularity` name is gone — apptainer doesn't ship a compatibility
symlink). Fix is mechanical: replace `singularityce` →
`apptainer` and `singularity` → `apptainer` everywhere.

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

## Idempotent resubmission — check outputs before submitting

Before re-submitting a chained pipeline that crashed mid-way (or you
just want to top-up missing pieces), **audit existing outputs per
(unit, stage) at the granularity downstream consumers need.** Don't
trust a single coarse predicate like "stage M's main output exists"
as a proxy for "stage M is fully done" if downstream needs sub-unit
outputs (per-ROI, per-run, per-event-type).

Two failure modes if you don't:

1. **Duplicate compute** — the same job re-runs against the same
   input, wasting cluster slots and crowding the queue your *new*
   priority jobs need.
2. **Output overwrite races** — two running jobs writing to the
   same file. If they finish near-simultaneously and one has a bug,
   the bad one can clobber a good result. Worse, you might not
   notice for a long time.

Pattern: each pipeline stage gets a `done(unit, stage)` predicate
that checks the **exact** files downstream will read. The submit
script skips submission iff `done(unit, stage)` returns true.

```bash
done_stage() {
    local unit=$1 stage=$2
    case "$stage" in
        prf)   [[ -f "${OUT}/prf/${unit}/result.nii.gz" ]] ;;
        atlas) [[ -f "${OUT}/atlas/${unit}/inferred.mgz" ]] ;;
        af)    # per-(unit, roi) — coarser would lie
               local n=$(ls "${OUT}/af/${unit}/" 2>/dev/null \
                           | grep -oE 'roi-[A-Za-z0-9]+' | sort -u | wc -l)
               [[ "$n" -eq "$N_ROIS_EXPECTED" ]] ;;
    esac
}
```

Downstream blocks should be willing to submit with **no afterok dep**
when their predecessor was skipped (its output is already on disk).
Pass empty job-IDs through dep wiring; build `--dependency=afterok:$X`
only when `$X` is non-empty.

## Stale chunks from previous sweeps

Chunked-then-merged array pipelines write per-chunk files like
`chunks/chunk-NNNN-of-MMMM.npz` and then merge into the final
output. **Pitfall:** re-running with a different `MMMM` (e.g.,
switching from `N_CHUNKS=10` to `N_CHUNKS=40`) leaves orphan chunks
with the old suffix in `chunks/`. The merge script — which usually
parses `MMMM` from the first chunk and counts files vs that total —
silently picks up the wrong total, mis-concatenates, or errors with
`K chunk files found but expected M`. Cascade: merge FAILED →
downstream `afterok` jobs all `DependencyNeverSatisfied`.

**Fixes (any one works; the third is the most robust):**

```bash
# 1. Wipe chunks/ before resubmit (idempotent restart):
rm -rf "${OUT}/${unit}/chunks/"

# 2. Selective delete: keep only chunks matching the current MMMM:
find "${OUT}/${unit}/chunks" -name 'chunk-*-of-*' \
    ! -name "chunk-*-of-$(printf '%04d' $N_CHUNKS).*" -delete

# 3. Make the merge script glob by the current MMMM, not all:
glob_pattern="chunk-*-of-$(printf '%04d' $N_CHUNKS).npz"
chunks=$(ls "${chunks_dir}/${glob_pattern}")
```

Symptom when you've been bitten: a couple of subjects'/units' merges
fail while others succeed, and the failed ones are exactly the ones
whose `chunks/` dir hadn't been cleared from a previous attempt
that used a different `N_CHUNKS`.

## Mid-flight partition swap with `scontrol update`

When fairshare throttles jobs on a busy partition (`Reason=Priority`
despite idle nodes on a sibling like `lowprio` that uses the same
hardware), don't cancel and resubmit — you'd break `afterok` chains.
Instead, **rewrite the partition on pending jobs in place**:

```bash
for jid in $(squeue --me -t PD -h -o '%i' \
             | awk -F_ '/^[0-9]+/ {print $1}' | sort -u); do
    scontrol update jobid=$jid Partition=lowprio Account=<new-account>
done
```

Properties:
- Works on **pending jobs only**. Running jobs keep their current
  partition.
- **JobIDs are preserved**, so every `afterok:$JID` downstream still
  points at the right parent — the dep graph is unchanged.
- Can also update `Account=` in the same command. Useful when you
  notice mid-flight that you've been submitting under a legacy
  account.
- Effect is immediate: re-dispatch typically lands within ~30 s
  if the new partition has free slots.

The cost is the usual `lowprio` (or whichever sibling you move to)
trade-off — typically lower job priority and/or preempt risk. Worth
checking the destination partition's preempt policy before mass-moving
critical-path work.

## Reading SLURM exit codes — the two "OOM"s aren't the same

`sacct -X --format=JobID,State,ExitCode` is the first thing to look
at when a job class fails repeatedly. The two patterns that look
like "out of memory" but mean very different things:

- **`State=OUT_OF_MEMORY`, `ExitCode=0:125`** — the kernel SIGKILL'd
  the process because the cgroup enforcing `--mem` exceeded its
  budget. **Host RAM** problem. Either bump `--mem`, reduce the
  workload (smaller batch / chunk), or check whether the job is
  silently running on CPU when it should be on GPU (CPU TF needs
  much more host RAM than GPU TF — the gradient tape moves from
  VRAM to DRAM).
- **`State=FAILED`, `ExitCode=1:0`** — Python raised and exited 1.
  Could be `tensorflow.python.framework.errors_impl.ResourceExhaustedError`
  (that's **GPU VRAM** OOM), an assertion, a NaN/Inf, an import
  error, etc. The traceback is in the log; read it.
- **`State=TIMEOUT`** — walltime hit. Bump `--time` if the job
  genuinely needs longer, or investigate whether it's running
  silently degraded (CPU fallback → 25× slower → can't finish in
  time).

The colloquial "the job OOM'd" usually means `0:125` if it's host
RAM, `1:0 + ResourceExhaustedError` if it's GPU VRAM. They have
different fixes; don't conflate them.

## Cancelling chains: by JobID range, not by name

When a chain breaks and you want to cancel everything downstream
from an old broken submission, **filter by parent JobID range, not
job-name substring.** Many job classes (especially aggregator /
analysis stages) are named generically across all subjects (e.g.,
`fit_attention_model`, `dog_dyn_target_shS`, `prf_merge`); a
"contains sub-13" filter misses them and leaves orphans that
generate fresh `DependencyNeverSatisfied` waves an hour later.

```bash
# Cancel any of my PENDING jobs whose parent JobID falls in a range
# (typically: "everything from the broken pre-fix submission wave"):
squeue --me -t PD -h -o '%i' \
    | awk -F_ '{print $1}' | sort -u \
    | awk -v lo=3019000 -v hi=3022000 '$1 >= lo && $1 < hi' \
    | xargs -r scancel
```

The JobID monotone-increases per submission; pick a cutoff right
after your fix landed, cancel everything below it, resubmit.

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

## Split aggregation from plotting

Aggregate many small files into one summary TSV on the cluster
(`srun -c 2 --mem 8G --time 5`), then `rsync` the summary back and
plot locally. Local iteration is faster (no queue wait, no module
load, PDF opens in Preview immediately). Full pattern + heuristic
(a few MB cutoff) lives in the user's global CLAUDE.md.

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
Conda envs that bundle their own CUDA runtime (`jax[cuda12]`,
`tensorflow[and-cuda]` wheels) work without any `module load` at
all, since SLURM sets `CUDA_VISIBLE_DEVICES` from the `--gres`
allocation and the bundled CUDA libs handle the rest. Reserve
`module load cuda/...` for envs that explicitly need the system
CUDA stack (rare). If a custom env DOESN'T bundle CUDA, follow the
module-loading rules in the next section.

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

### Porting GPU → CPU: memory budget doesn't transfer

When GPU queues are congested and you're tempted to switch to CPU
on the same script, **don't assume the per-task memory budget is
unchanged**. GPU TF / cuBLAS / cuDNN use tile fusion that keeps
matmul intermediates inside on-chip scratch — large `(M, K) @ (K, N)`
operations never materialize the full `(M, K, N)` tensor in DRAM.
CPU TF + OpenBLAS materializes more intermediates and is much more
sensitive to inner-batch size.

Concrete symptom: a parameter-fitting script with
`--voxel-chunk-size 100000` runs fine on a 16 GB GPU but
`OUT_OF_MEMORY`-kills at 16 GB CPU mem within 2 minutes. The fix is
to shrink the inner batch (typically 5-10×) — not to bump `--mem`
indefinitely.

Rule of thumb: when moving a TF fitting workload GPU → CPU, halve
the inner-chunk size and re-measure peak RSS on one task before
launching the array. Easier still: stay on GPU and use the
[lowprio partition](#mid-flight-partition-swap-with-scontrol-update)
if the standard GPU queue is the bottleneck — same hardware, faster
dispatch.

### cuInit race on multi-GPU nodes

Multiple jobs landing simultaneously on the same multi-GPU node
(8-GPU V100 / A100 / H100 boxes) issue parallel `cuInit` calls that
deadlock the NVIDIA driver. TF silently falls back to CPU → ~25×
slowdown → walltime timeouts → cascading `DependencyNeverSatisfied`.

Random stagger doesn't reliably fix this — with 8 jobs racing in a
30 s window, the probability that all start ≥ 1 s apart (the driver
init window) is ~10%. Empirically ~90% deadlock.

**Fix: per-node `flock` warm-up.** First job per node does a
minimal CUDA init under an exclusive lock; subsequent jobs see a
warm driver.

```bash
LOCK="/tmp/cuinit_warm_$(hostname -s).flock"
(
    flock -w 60 -x 200 || { echo "WARN: lock timeout"; exit 0; }
    "$PYTHON" -c "
import os
os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '3')
import tensorflow as tf
print(f'cuInit OK: {len(tf.config.list_physical_devices(\"GPU\"))} GPU(s)', flush=True)
"
) 200>"$LOCK"
```

Properties: `/tmp` is node-local (NFS locks would be wrong); kernel
releases `flock` on holder death (crash-safe); `-w 60` timeout
prevents indefinite hangs.

Keep a short random stagger (`sleep $((RANDOM % 15))`) separately
for the **NFS dogpile** at task start — different race, unrelated
to cuInit. `ArrayTaskThrottle` mitigates NFS dogpile but doesn't
prevent cuInit races — 8 of 50 concurrent tasks can still land on
the same node.

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

## Pipeline orchestration: use Snakemake, not bash submitters

For multi-stage pipelines (multiple subjects × models × ROIs with
inter-stage dependencies), Snakemake on top of SLURM is cleaner than
hand-written bash submitters with `afterok` chains: DAG inference
from input/output paths, automatic per-subject isolation, recovery
from partial failures, and a single place where the chain is
specified.

**Snakemake-specific knowledge** — driver placement (NEVER on the
login node, the per-job Timer threads blow past `ulimit -u`), rule
output conventions for per-wildcard outputs, why the SLURM plugin
gives jobs UUID names and how to read the `--comment` field instead,
recovery after a crashed driver, QoS walltime caps — lives in the
**`snakemake`** skill. Designed to be read together: this skill for
the SLURM side, that one for the Snakemake-on-SLURM overlay.

## Long runs: always provide a visible progress signal

Whenever you launch something that takes longer than ~1 minute on
the cluster (model fitting, simulations, big preprocessing, batch
jobs), make sure progress is visible — either live in a tail-able
log file or via a built-in progress bar (`pm.sample(progressbar=True)`,
`tqdm`, etc.) with `python -u` + `PYTHONUNBUFFERED=1` so updates
flush promptly. If absolutely nothing is available, print a periodic
flushed status line.
