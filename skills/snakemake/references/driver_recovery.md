# Recovery from a crashed Snakemake driver

**When to load:** the driver was `scancel`'d, OOM-killed, hit walltime,
or otherwise didn't exit cleanly, and the next driver start dies
within ~10 seconds with `LockException` or `IncompleteFilesException`.

`scancel` (and any non-clean driver exit) leaves two kinds of stale
state in `.snakemake/`, which surface as **two different exceptions**
on the next driver run. Both fire instantly (within a few seconds),
so a driver that dies in `<10s` is almost always one of these — not
a config bug.

| Symptom | Cause | Fix |
| --- | --- | --- |
| `LockException: Directory cannot be locked …` | Stale `.snakemake/lock` from prior driver | `snakemake … --unlock` (idempotent — safe to always run) |
| `IncompleteFilesException` listing N files | Output files marked incomplete in metadata | `snakemake … --rerun-incomplete` |

These are independent failure modes — `--rerun-incomplete` does NOT
unlock, and `--unlock` does NOT clear the incomplete-files flag. A
driver that gets killed mid-flight will leave a lock (always) and
*may* leave incomplete files (depends on which rules were running).

## Bake both into `run_driver.sh`

So re-submission just works (`references/run_driver.sh` already does this):

```bash
# Idempotent unlock — does nothing if no lock exists.
snakemake … --unlock || true

exec snakemake … --rerun-incomplete
```

The `|| true` matters: when there's no lock, `--unlock` exits non-zero
on some versions, which under `set -e` would kill the driver script
before the real snakemake call.

## When `--rerun-incomplete` rebuilds too much

Alternative: `snakemake --cleanup-metadata <files>` marks specific
outputs as metadata-clean without touching the file contents. Useful
when you know the file is fine but Snakemake's metadata says
otherwise — e.g. after manually fixing up a half-written output.
