# Logs and job-name conventions

**When to load:** writing a new SLURM script (especially an array job),
or trying to find the log for a job that's already running but the
log isn't where you expected.

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

## Job-name convention

Always set an informative `--job-name`. Encode *what* + key parameters
(analysis name, model index, subject id). Generic names like `prf_gpu`
are useless when the queue scrolls. Examples: `prf_m1_sub-02`,
`prf_merge_m1`, `glmsingle_sub-08`.

## Renaming an array task in-script

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
