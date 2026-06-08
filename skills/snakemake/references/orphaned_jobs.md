# Don't preserve in-flight jobs across a driver restart

**When to load:** about to `scancel` the Snakemake driver while it has
expensive long-running jobs in flight (fmriprep, neuropythy, anything
hours-long) and you're tempted to keep those jobs alive so you don't
lose compute.

**TL;DR:** cancel the driver's **entire** run-UUID job set together, or
don't restart at all. Mixing the two breaks Snakemake's coordination
guarantee.

## The failure mode: silent duplicate dispatch + scratch racing

Snakemake's slurm plugin hardcodes `--job-name <run-uuid>` for every job
it dispatches. The driver tracks its in-flight jobs by that UUID. When
you `scancel` the driver but leave some of its jobs running:

- The next driver start has its **own** new UUID. It cannot see the
  preserved jobs from the old UUID — they don't appear in its tracking
  table.
- The new driver consults the DAG: which outputs don't exist? If the
  preserved job hasn't finished yet, **its output sentinel is still
  missing**.
- → The new driver dispatches a fresh job for the same rule. Now you
  have two concurrent jobs working on the same wildcards.
- Both jobs share `/scratch/<user>/.../<wildcards>_wf/` (apptainer `-w`
  bind, neuropythy work dir, etc.) and overwrite each other's gzip
  intermediates → `ZRAN_READ_FAIL`, half-written NIfTIs, mysterious
  workflow node failures with no obvious cause.

## Concrete incident — abstract_values, 2026-05-29

- Driver A dispatched fmriprep for sub-11 (job 3573304) + sub-12 (3573299).
- I `scancel`'d Driver A but excluded the fmripreps from the cancel
  ("keep the long ones, they'll save us 5 hours").
- Driver B launched a few minutes later. No record of 3573304 / 3573299.
  Dispatched another sub-11 fmriprep (3573622). Two concurrent
  fmripreps sharing `/scratch/gdehol/fmriprep_25_2_wf/sub_11_ses_1-2_wf/`.
- ZRAN_READ_FAIL on a gzip workflow file → sub-12's run failed
  internally; apptainer exit 1; fmriprep wrote a *failure-summary HTML*;
  the script's html-tolerance fallback misread that as success.
- Snakemake marked sub-12 fmriprep done. Downstream mask-creation rules
  fired against missing ses-2/anat outputs and broke.
- Recovery cost: ~4 h fmriprep compute lost + ~2 h debugging the chain
  of "why did this rule fail / why is this dir empty / why is the driver
  re-dispatching" before the racing root cause surfaced.

## How to do it right

If you must restart the driver:

```bash
# 1. Find the driver's run UUID
ssh <cluster> "squeue -u $USER -h -o '%i %j' | awk '\$2 ~ /^[0-9a-f-]{36}$/' | head"

# 2. Cancel the driver AND all its UUID-named children together
ssh <cluster> "scancel --name=<project>_snake_driver --name=<run-uuid>"

# 3. THEN launch the new driver
ssh <cluster> "cd ~/git/<project> && sbatch <project>/snakemake/run_driver.sh"
```

`--name=` accepts multiple `--name=` flags in one invocation and cancels
all matches atomically.

## Better: don't restart unless you have to

The driver is designed to keep running. For small surgery, prefer one
of these over a full restart:

- **Config-only change** (subjects list, resource bumps): edit
  `config.yaml`, `git pull` from the running driver's node, signal
  the driver with `kill -HUP <pid>` if it supports config reload, OR
  just let it finish the current dispatch cycle and pick up the new
  config on the next polling tick (`seconds-between-status-checks: 30`).
- **Backfilling sentinels for legacy outputs**: touch the files
  on disk; Snakemake re-checks output existence on its next DAG
  evaluation tick without a restart.
- **Rule logic fix**: requires restart. Cancel all UUID-named jobs as
  shown above; don't try to preserve.

The 5 hours of fmriprep compute you'd "save" by preserving an in-flight
job costs more than 5 hours when it racing-corrupts another in-flight
job and you have to redo both.

## See also

- [`driver_recovery.md`](driver_recovery.md) — `LockException` /
  `IncompleteFilesException` after a clean restart with NO racing jobs.
  Different failure mode; load when the driver dies <10s after start.
- [`monitoring.md`](monitoring.md) — finding the run UUID + reading the
  `Comment` field to know which rule+wildcards each opaque-named job
  is processing.
