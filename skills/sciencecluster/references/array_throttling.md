# Throttling SLURM arrays — `%N` and `ArrayTaskThrottle`

**When to load:** about to submit an array of ~100+ tasks, or seeing
`user env retrieval failed requeued held` on tasks of a freshly
submitted array.

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

## `--export=ALL` makes this much more likely — usually drop it

`--export=ALL` (and bare `--export=ALL,VAR=x`) tells SLURM to *retrieve the
submitting user's environment* on each compute node, which is precisely the
step that fails under load. Four arrays of 19 tasks submitted back-to-back
put **all 44 pending tasks** into `user env retrieval failed requeued held`
on 2026-08-05 — well under the ~100-task threshold above, because the
`--export=ALL` retrieval multiplies the per-task cost.

If the job script sources conda itself (`. $HOME/init_conda.sh && conda
activate <env>`, which every template here does) it does **not** need the
login environment. Pass only what the script actually reads:

```bash
# fragile: forces per-task env retrieval
sbatch --array=1-19 --export=ALL,NVOX=100,TAG=nvox100 job.sh

# robust: SLURM ships just these two variables
sbatch --array=1-19 --export=NVOX=100,TAG=nvox100 job.sh
```

Recovery for an already-held set — release them all in one call, they usually
run fine on the retry:

```bash
scontrol release $(squeue -u $USER -h -r -t PD -o "%i %R" \
    | grep -i held | awk '{print $1}' | paste -sd, -)
```

Check it worked with `squeue -u $USER -h -r -t PD -o "%R" | sort | uniq -c`:
the reason should change from `(... held)` to `(Priority)`.

## Semantics

**`ArrayTaskThrottle=N` caps concurrent *running* tasks, not just
dispatch rate.** With `%50`, at most 50 of an array's tasks run in
parallel; the rest stay PD until a slot frees. Costs some wallclock
if you have more CPUs than the cap, but it's the only knob SLURM
exposes to limit task starts.

## Sensible defaults

- `%50` — mild throttle, good for arrays of ~50–500 tasks. Stops
  the worst dogpile waves.
- `%150` — looser, only useful for very large arrays (1000+) when
  you want most-but-not-all running concurrently.
- No throttle — for arrays under ~30 tasks the dogpile risk is low.

## Cross-array dogpile

**Across many parallel arrays the dogpile is global** (NFS reads from
`$HOME` regardless of which array). Per-array throttling mitigates
but doesn't eliminate. If you keep seeing held tasks even with
throttles, batch your `sbatch` calls with `sleep 30` between them.

## Releasing held tasks

```bash
squeue --me -h -t PD --format='%i %r' \
  | awk '/user env/ {print $1}' \
  | xargs -I {} scontrol release {}
```
