# QoS walltime caps and driver re-submission

**When to load:** the driver `sbatch` returns `Invalid qos
specification` or `Time limit request exceeds partition's limit`, or
you're picking the QoS for `run_driver.sh` and need to know what
walltime is allowed.

Many clusters tie partition × QoS to max walltime. **UZH sciencecluster**
(see also the `sciencecluster` skill's constants table):

| QoS | Max walltime | Notes |
| --- | ------------ | ----- |
| normal | 1-00:00:00 | only QoS allowed on `lowprio` |
| medium | 2-00:00:00 | `standard` partition |
| long   | 7-00:00:00 | `standard`, MaxJobsPU=24 |
| debug  | 4 min      | priority 1, MaxJobsPU=1 |

Submitting `--time=2-00:00:00` on `lowprio` returns
**`Invalid qos specification`** with no further detail. Fix: either
drop to 1 day (`lowprio`) or switch partition + qos
(`#SBATCH --partition=standard --qos=medium`).

## When a 24h driver runs out

Snakemake's persistence layer (`.snakemake/`) means a resubmit of the
same `run_driver.sh` picks up where it left off — losing only the
dispatch state (jobs that were in flight may have completed by the
time the new driver starts; Snakemake re-checks output files on
startup and skips rules whose outputs are already on disk).

The `--unlock || true` + `--rerun-incomplete` dance baked into
`references/run_driver.sh` is what makes "kill and resubmit the
driver" a one-command operation. See `driver_recovery.md` for the
recovery details.
