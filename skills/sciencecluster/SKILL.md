---
name: sciencecluster
description: SLURM cluster (UZH sciencecluster) operational knowledge — submitting jobs, conda activation in SLURM context, GPU constraints, log conventions, common failure modes (NFS dogpile, cuInit race, partition contention), and cluster-only vs local code paths. Use this skill whenever the user is working with sciencecluster, SLURM (sbatch, squeue, scontrol, sacct), conda envs on the cluster, GPU jobs with `--gres`, the user mentions "the cluster", or the working directory contains a `slurm_jobs/` folder. Also use for diagnosing held / failed / zombie SLURM jobs.
---

# UZH sciencecluster — SLURM operational knowledge

Operational knowledge for the UZH sciencecluster. Cluster-wide
constants (partition names, QoS values, login host, GPU types) are
baked in verbatim. Per-user values (SLURM account, conda paths,
project env names) are written as `<angle-bracket>` placeholders that
the user/agent fills in from their private global config or the
project's CLAUDE.md.

**The body of this skill is short on purpose.** Constants, golden
rules that apply to every job, and a reference index — that's it.
Topical playbooks (apptainer, GPU jobs, cuInit race, exit codes,
partition swap, …) live in `references/` and load on demand. If you
hit a symptom that matches a reference title, read that file.

## Constants

| Thing | Value |
|---|---|
| SSH alias (typical) | `sciencecluster` |
| Login host | `cluster.s3it.uzh.ch` |
| Partitions | `lowprio` (fast dispatch, **preemptable**), `standard` (fairshare) |
| QoSes | `debug` (4 min, MaxJobsPU=1, +prio), `normal` (1 day, default), `medium` (2 day, `standard` only), `long` (7 day, MaxJobsPU=24) |
| GPU types | L4 (1/node, no cuInit race), V100 (8/node), A100 (8/node), H100/H200 (CUDA 12, exclude when env is on CUDA 11) |
| Shared data root | `/shares/<account>/` (per-account; group-owned share) |

> **Partition convention** (not enforced by policy): reserve `lowprio`
> for jobs that are GPU-bound, or short and easily resumable.
> Multi-hour CPU jobs (fmriprep, GLMsingle, encoding fits) belong on
> `standard` + `medium` (≤2 d) or `long` (≤7 d). `lowprio` is
> preemptable, so long non-resumable CPU work invites rework when a
> higher-priority job claims the node mid-flight.

Per-user placeholders (substitute from the project's CLAUDE.md):

- `<account>` — your SLURM account (e.g. `zne.uzh`)
- `<conda-base>` — conda install root (e.g. `~/data/miniforge3`)
- `<conda-envs>` — envs dir (e.g. `~/data/conda/envs`)
- `<env>` — project conda env name (e.g. `retsupp_cuda`)

## Templates

Copy-pasteable SLURM scaffolding lives in `references/`:

- `array_cpu_template.sh` — CPU array job (stagger + logging + conda activation)
- `array_gpu_template.sh` — same, plus `--gres=gpu:1`, GPU constraint, cuInit-race defense
- `submit_chain.sh` — orchestrator that wires per-subject `afterok` chains

Fill the placeholders before submitting.

## Golden rules (apply to every job)

**1. Never run compute on the login node.** The login node is shared
across all users; `ulimit -u` is 256, and even a "diagnostic" script
that imports nilearn/TF or loads a large NIfTI is heavy enough to
slow other people's `ls` and `squeue` and risk an admin kill. For
diagnostics: pull data local and run on your laptop, or `srun --pty`
for an interactive compute-node shell, or wrap in
`sbatch --time=00:10:00`. Only pure stat queries (`squeue`, `sacct`,
`ls`, `head`, `wc -l`, `git pull`) belong on the login node.

**2. Always `git pull` on the cluster before submitting.** Sync code
via git — commit local, push, `git pull` on the cluster. **Never**
rsync individual files into the cluster's repo working tree (skips
commit history, breaks the always-pull invariant, silently misplaces
files when paths don't match). If the cluster has uncommitted
job-script tweaks, `git stash` → `git pull` → `git stash pop`.

```bash
# local
git add path/to/new_script.py path/to/new_job.sh
git commit -m "Add ..."
git push

# cluster
ssh sciencecluster 'cd ~/git/<project> && git stash && git pull && git stash pop'
```

**3. Inside the SLURM script — shell + conda setup:**

```bash
#!/bin/bash             # use #!/bin/bash -l if you need `module load …`
set -eo pipefail        # NOT set -u (conda activation aborts under -u)

source "<conda-base>/etc/profile.d/conda.sh"
conda activate <env>
export PYTHONUNBUFFERED=1
python -u script.py

# Equivalent: skip activation, use env binary directly
export PYTHONUNBUFFERED=1
<conda-envs>/<env>/bin/python -u script.py
```

The non-obvious bits:

- **`PYTHONUNBUFFERED=1` + `python -u`** — no downside in batch
  contexts; without them logs only flush when buffers fill, which
  hides a stuck job for hours.
- **`conda run -n <env> python` BUFFERS ALL STDOUT until the process
  exits** — `python -u` and `PYTHONUNBUFFERED=1` do NOT fix it, because
  `conda run` itself captures the child's pipe. Failure signature: the
  `.txt` log sits frozen at the first few lines for the entire run, so
  you cannot tell a working job from a hung one (`sstat -j <id>
  --format=AveCPU` will show CPU accruing — that's the only live signal).
  **Two fixes, in order of preference:**
  1. **Use the env binary directly** — `<conda-envs>/<env>/bin/python -u
     script.py` (no activation, no wrapper, no buffering). This is the
     default for one-shot job scripts.
  2. If you must keep `conda run` (e.g. matching an existing repo
     convention), it **must** be `conda run --no-capture-output -n <env>
     python -u …`.
  When editing or adding any `slurm_jobs/*.sh`, check this — many older
  repo scripts still use bare `conda run` and will silently buffer.
- **No `set -u`** — conda activation scripts reference unset vars
  (`$ADDR2LINE`, `$AR`, `$CC`) and abort. Job dies in <5 s with
  `FAILED 1:0`, `Elapsed=00:00:02`.
- **The `init_conda.sh` indirection has occasionally failed** inside
  SLURM jobs (unclear cause). Source `conda.sh` directly.
- If you need `module load …`, switch the shebang to `#!/bin/bash -l`
  — see `references/script_shell_setup.md` for why plain `#!/bin/bash`
  silently breaks `module` and `MODULEPATH`.
- **Same trap applies to `srun bash -c "..."`.** That spawns a
  non-login non-interactive bash where `module` isn't defined, so the
  `module load apptainer` line fails silently (`apptainer: command not
  found`) and downstream commands abort. Use `srun bash -lc "..."`
  (login shell) instead. Verified on UZH sciencecluster 2026-05.

**4. Keep `--time` tight.** Fair-share favors tight walltime requests.
A 24 h request waits longer than a 30-min one even if both run for
10 min. Set `--time` to ~2× the actual expected runtime; calibrate
with `sacct --format=JobID,JobName,Elapsed | grep <jobname>`.

**5. Always emit a visible progress signal** on anything that runs
>1 minute — a tail-able log line, a `tqdm` bar,
`pm.sample(progressbar=True)`, etc. — with `PYTHONUNBUFFERED=1` so
updates flush promptly. For long sweeps/loops, prefer **writing each
result row to the output file and `flush()`-ing as you go** rather than
collecting everything and writing once at the end: the growing file is a
progress meter that survives stdout buffering AND a wall-time kill (an
end-only write means a timeout loses the entire job's output). The
row-count (`wc -l`) tells you exactly how far it got.

**6. Orchestrate multi-stage pipelines with Snakemake**, not
hand-written `afterok` chains. See the **`snakemake`** skill for the
SLURM-aware specifics (driver placement, plugin quirks, recovery
after a crashed driver). This skill and that one are designed to be
read together.

## Building conda envs: sbatch the build, but **no GPU node needed**

For the modern pip-wheel CUDA stack
(`tensorflow[and-cuda]`, `jax[cuda12]`, `torch+cu*`) you do **not**
need `--gres=gpu:1` to build the env — even for full CUDA stacks.
Those wheels are precompiled and ship their own CUDA runtime via
`nvidia-cuda-runtime-cu*` / `nvidia-cudnn-cu*` packages; the install
is just wheel extraction, no compilation, no driver probe. CUDA
initializes lazily at first device-use inside the running job.

**Verified end-to-end on sciencecluster 2026-05-27:** env built on a
`standard` CPU node (no GPU visible, no `nvidia-smi`), then activated
on a `--gres=gpu:1` job — TF 2.20, JAX 0.10, and torch 2.12+cu130 all
detected the L4 and ran matmul without any post-install fixup.

So: sbatch the build (login-node ulimit rule applies — `conda` +
`pip` fork too many processes) to `lowprio` or `standard` with no
`--gres`. Faster dispatch, and you don't burn a GPU slot just to
unpack wheels. Legacy `create_gpu_env.sh` scripts on older projects
(`tms_risk` etc.) that still ask for `--gres=gpu:1` are carryover
from the pre-bundled-wheels era — drop the `--gres` next time you
touch them.

Cases where you would still need a GPU at build: `pip install
--no-binary :all: <pkg>`, or custom CUDA-kernel compilation. Full
operational details (paths convention, build sbatch template, solver
notes) in `references/conda_envs.md`.

## Reference index

Load these on demand — each is a focused playbook, not required
reading.

**Conda envs**

- `references/conda_envs.md` — paths convention, build sbatch
  template, why a GPU node isn't needed for the build, when it still
  would be, solver speed notes

**Inside the SLURM script**

- `references/script_shell_setup.md` — `#!/bin/bash -l`, `module`,
  why `.bashrc` doesn't fix it
- `references/containers_apptainer.md` — apptainer (not singularity);
  reusing FreeSurfer / etc. from sandbox containers via PATH
- `references/gpu_jobs.md` — `--gres=gpu:1`, GPU constraints, GPU→CPU
  memory pitfall, cuInit race + `flock` warm-up
- `references/logs_and_naming.md` — `~/logs/<jobname>_<jobid>.txt`
  redirect, `--job-name` convention, `scontrol update name=` for
  arrays

**Submission lifecycle**

- `references/debug_qos.md` — `--qos=debug` fast-lane smoke tests
  when fair-share has buried you
- `references/array_throttling.md` — `%N` and `ArrayTaskThrottle`
  for NFS dogpile; releasing `user env retrieval failed requeued held`
  tasks
- `references/idempotent_resubmit.md` — per-(unit, stage) `done()`
  predicates; stale-chunk pitfall with `chunk-NNNN-of-MMMM.npz`
- `references/partition_swap.md` — `scontrol update Partition=` on PD
  jobs (preserves JobIDs, keeps `afterok` graph intact)
- `references/cancel_and_zombies.md` — cancel by JobID range, sweep
  `DependencyNeverSatisfied` zombies

**Diagnosis**

- `references/exit_codes.md` — `0:125` (host RAM) vs `1:0` (GPU VRAM
  / Python raise) vs `TIMEOUT`

**Workstation hygiene**

- `references/ssh_multiplexing.md` — `ControlMaster auto` to dodge
  the login-host connection rate limit
