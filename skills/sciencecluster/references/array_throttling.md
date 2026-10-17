# Throttling SLURM arrays — `%N` and `ArrayTaskThrottle`

**When to load:** about to submit an array of ~100+ SHORT tasks; seeing
`user env retrieval failed requeued held` on a freshly submitted array;
or seeing `Reason=JobArrayTaskLimit` on pending tasks and wondering
whose limit it is.

## Read this first: throttling buys you nothing after the tasks have started

The only problem `%N` solves is a **startup** problem. Many tasks
dispatching in the same second dogpile NFS reading each task's
`$HOME/.bashrc` / `~/.zshrc`; some then fail with `user env retrieval
failed requeued held` and sit held until released. That is a burst at
`t = 0`, over within a minute or two.

`ArrayTaskThrottle`, though, caps concurrently **running** tasks for the
array's whole life. So it pays a cost proportional to the job's WALLTIME
to fix a problem that lives in the first two minutes. On an array of long
jobs that trade is terrible:

    14 tasks x 8 h each, %10  ->  two waves, ~16 h wallclock
    14 tasks x 8 h each, no %  ->  one wave,  ~8 h wallclock

A whole day lost, on a cluster that had 2 100 idle cores. **Match the knob
to the problem: stagger the starts, don't cap the concurrency.**

## Prefer the in-script stagger

`array_cpu_template.sh` / `array_gpu_template.sh` already carry

```bash
sleep $(( RANDOM % 30 ))
```

before anything touches `$HOME`. That spreads the env-retrieval burst over
30 s at zero wallclock cost and makes `%N` unnecessary for almost every
array these templates run. **If the script staggers, do not also throttle.**
Widen the stagger (`% 60`, `% 120`) before reaching for `%N`.

## When a throttle IS right

- Arrays of **hundreds of short tasks** (minutes each), where the wallclock
  cost of capping concurrency is small and the dispatch burst is large.
- You are **deliberately being a good citizen** on a busy partition — but
  check `sinfo` first (below); usually there is plenty idle and the polite
  gesture only slows you down.
- A per-task resource that genuinely does not parallelise: one licence, one
  writable scratch dir, an external API with a rate limit.

## When it is NOT

- **Long jobs.** Anything over ~1 h per task: the wave structure dominates.
- **Small arrays** (under ~30 tasks). Under the dogpile threshold anyway.
- **Arrays that already stagger in-script.** Belt and braces, all cost.
- **"To be safe."** A throttle is not free and not neutral; it is a wallclock
  tax. Justify it or leave it off.

## Defaults

- **No throttle** — the default. Arrays under ~100 tasks, or any array whose
  tasks stagger in-script.
- `%100` — arrays of many hundreds of short tasks without an in-script stagger.
- `%50` — only when something genuinely serialises (a lock, a licence, an API).

(These are looser than they used to be. The old `%50`-for-50-tasks advice was
written from one bad dogpile day and cost far more wallclock than it ever
saved.)

## `Reason=JobArrayTaskLimit` is almost always self-inflicted

```
5704658_[10-13]  ladder15  PD  0:00   JobArrayTaskLimit
```

This means **your own `%N`**, not a cluster policy. Confirm and lift:

```bash
scontrol show job <ARRAY_JOB_ID> | grep -E 'ArrayTaskId|ArrayTaskThrottle'
#   ArrayTaskId=10-13%10   ArrayTaskThrottle=10     <- yours

scontrol update JobId=<ARRAY_JOB_ID> ArrayTaskThrottle=<bigger, or 0 for none>
```

The pending tasks' reason should flip to `Priority` (genuinely queued behind
fair-share) or they start immediately. Raising it mid-flight is safe and does
not disturb running tasks.

Before raising, check there is actually room:

```bash
sinfo -o "%.15P %.6a %.6D %.6t %C"     # CPUS shown as Alloc/Idle/Other/Total
```

Cluster-imposed limits look different and are worth ruling out once:

```bash
scontrol show config | grep -iE "MaxArraySize|MaxJobCount"
sacctmgr -nP show assoc user=$USER format=Account,MaxJobs,MaxSubmit,GrpTRES
```

On sciencecluster (checked 2026-09-09) `MaxArraySize=50000`,
`MaxJobCount=100000`, and no per-user `MaxJobs`/`MaxSubmit`/`GrpTRES` on
either account — so **every `JobArrayTaskLimit` you see there is your own**.
Other reasons that are NOT yours: `AssocMaxJobsLimit`, `QOSMaxJobsPerUserLimit`,
`Resources`, `Priority`.

## `--export=ALL` makes the dogpile much more likely — usually drop it

`--export=ALL` (and bare `--export=ALL,VAR=x`) tells SLURM to *retrieve the
submitting user's environment* on each compute node, which is precisely the
step that fails under load. Four arrays of 19 tasks submitted back-to-back put
**all 44 pending tasks** into `user env retrieval failed requeued held` on
2026-08-05 — well under the ~100-task threshold, because the `--export=ALL`
retrieval multiplies the per-task cost.

If the job script sources conda itself (`. $HOME/init_conda.sh && conda
activate <env>`, which every template here does) it does **not** need the login
environment. Pass only what the script actually reads:

```bash
# fragile: forces per-task env retrieval
sbatch --array=1-19 --export=ALL,NVOX=100,TAG=nvox100 job.sh

# robust: SLURM ships just these two variables
sbatch --array=1-19 --export=NVOX=100,TAG=nvox100 job.sh
```

**Dropping `--export=ALL` is a better fix than throttling** — it removes the
cause instead of spreading it out, and costs no wallclock.

## Semantics

`ArrayTaskThrottle=N` caps concurrent *running* tasks, not the dispatch rate.
With `%50`, at most 50 of the array's tasks run in parallel; the rest stay PD
until a slot frees. There is no SLURM knob that limits only the start rate —
which is exactly why the in-script `sleep` is the better tool.

## Releasing held tasks

```bash
squeue --me -h -t PD --format='%i %r' \
  | awk '/user env/ {print $1}' \
  | xargs -I {} scontrol release {}
```

Or in one call:

```bash
scontrol release $(squeue -u $USER -h -r -t PD -o "%i %R" \
    | grep -i held | awk '{print $1}' | paste -sd, -)
```

Check with `squeue -u $USER -h -r -t PD -o "%R" | sort | uniq -c`: the reason
should change from `(... held)` to `(Priority)`.

## Cross-array dogpile

Across many parallel arrays the dogpile is global (NFS reads from `$HOME`
regardless of which array). If held tasks keep appearing even without
`--export=ALL`, put `sleep 30` between your `sbatch` calls rather than
throttling each array.
