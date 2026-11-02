# Throttling SLURM arrays — `%N` and `ArrayTaskThrottle`

**When to load:** about to add `%N` to an array; or seeing
`Reason=JobArrayTaskLimit` on pending tasks and wondering whose limit it is.

**Not for `user env retrieval failed requeued held`.** That hold comes from
passing an `--export` list (also `--export=ALL,VAR=x`), and throttling, an
in-script `sleep` stagger or pacing `sbatch` calls do nothing against it. See
the top of `SKILL.md`.

## Semantics

`ArrayTaskThrottle=N` (`--array=1-300%N`) caps the number of the array's tasks
that **run at the same time**, for the array's whole life. It is not a start-rate
limit; SLURM has no knob that only spreads out starts.

So it costs wallclock in proportion to the tasks' walltime:

    14 tasks x 8 h each, %10  ->  two waves, ~16 h wallclock
    14 tasks x 8 h each, no %  ->  one wave,  ~8 h wallclock

## When a throttle IS right

- A per-task resource that genuinely does not parallelise: one licence, one
  writable scratch dir, an external API with a rate limit, a shared output
  file.
- Hundreds of short tasks (minutes each) that all read the same large files
  from a network share at start-up, where the wallclock cost is small.
- Deliberately leaving room on a busy partition (check `sinfo` first; usually
  there is plenty idle).

Otherwise: **no throttle.** Long tasks, small arrays and "to be safe" are not
reasons. For the GPU cuInit race use the `flock` warm-up in
`references/gpu_jobs.md`, not `%N`.

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
