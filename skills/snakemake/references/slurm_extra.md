# `slurm_extra` is restricted

**When to load:** the driver reports `Submitting N ready jobs` and then
nothing happens (silent inaction), or you tried to pass `--gres`,
`--partition`, `--time`, etc. via `resources.slurm_extra` and want to
know why it's not working.

`snakemake-executor-plugin-slurm` owns these flags directly:

```
--job-name   --output     --export      --comment
--partition  --account    --gres        --constraint
--mem        --cpus-per-task            --time
```

Setting any of these via `resources.slurm_extra` raises `WorkflowError`
— and **the error gets swallowed by the thread pool**, so the symptom is
"Submitting N ready jobs" followed by silent inaction. Easy to chase
your tail looking for config bugs that aren't there.

## Use the plugin's first-class keys

```python
resources:
    slurm_partition="lowprio",
    slurm_account="zne.uzh",
    runtime=60,                # → --time
    mem_mb=24000,              # → --mem
    cpus_per_task=16,          # → --cpus-per-task
    # For GPUs:
    # slurm_extra="--gres=gpu:1 --constraint=L4",  # NO — use:
    gres="gpu:1",
    constraint="L4",
```

Only put truly free-form flags in `slurm_extra` (e.g., a custom
`--qos=foo` for cluster-specific quirks).
