# Monitoring: jobs have UUIDs, comments have meaning

**When to load:** you're trying to figure out what's running by looking
at `squeue` and every job has an opaque UUID for a name; or you want to
inspect what the driver thinks the pipeline state is without
disturbing it.

The `snakemake-executor-plugin-slurm` hardcodes `--job-name <run-uuid>`
for SLURM bookkeeping (so it can use `squeue --name <uuid>` for status
polls). You cannot override per rule — `slurm_extra` doesn't accept
`--job-name`. But the plugin also sets

```
--comment rule_<rule_name>_wildcards_<wildcards>
```

which DOES carry the rule + wildcard.

## Read the comment field

```bash
squeue -u $USER -h -O "JobID:14,State:10,TimeUsed:10,Comment:80"
```

A `status.sh` helper that parses the comment into per-rule counts is
in `references/status.sh`. Pair it with a `tail -f` on the latest
`driver_<jobid>.log` for a "live feed" experience.

## Deeper inspection while the driver is running

- `snakemake --summary` — text table of every target's done/missing/
  incomplete state. Reads on-disk `.snakemake/` persistence, doesn't
  disturb the live driver.
- `.snakemake/log/<run-id>.snakemake.log` — full driver log (more
  verbose than the captured stdout).
- `--rulegraph` and `--dag` — static structural views (need graphviz
  `dot` to render; can be piped to stdout as `.dot` text and rendered
  locally).
