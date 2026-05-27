# Smoke tests with `--qos=debug`

**When to load:** you've submitted many jobs and your fair-share
priority is in the gutter, but you need to validate a 5-second change
without waiting hours. Or you're iterating on a SLURM script and want
near-instant dispatch.

When you've submitted dozens to hundreds of your own jobs and the
fair-share scheduler has deprioritised everything else you submit,
even a 5-second sanity check sits in queue for hours. The fix is the
**`debug` QoS** — most clusters reserve a fast lane for short jobs.

On UZH sciencecluster: `debug` has `MaxWall=00:04:00` and
`Priority=+1`, dispatches in seconds. Sole catch: only 1 job per user
at a time (`MaxJobsPU=1`), so submit smokes one at a time.

```bash
sbatch --account=<account> --partition=standard --qos=debug \
       --time=00:04:00 --cpus-per-task=2 --mem=4G \
       --job-name=smoke --output=$HOME/logs/smoke_%j.log \
       /path/to/smoke.sh
```

## Don't `--wrap` for non-trivial commands

Don't use `--wrap "..."` for anything beyond a trivial one-liner —
the wrap is interpreted by `/bin/sh`, not `/bin/bash`, so `set -o
pipefail`, brace expansion, etc. fail. Write a real `.sh` script with
`#!/bin/bash` and pass that to sbatch.

## Inspect the QoS on the cluster

Check what `debug` looks like on your cluster:

```bash
sacctmgr show qos format=Name,Priority,MaxWall,MaxJobsPU --parsable2
```

When fair-share is in the way of a quick verification, this beats
"wait and check back in 3 hours."
