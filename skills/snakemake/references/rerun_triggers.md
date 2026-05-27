# `rerun-triggers`: drop `mtime` to stop chain cascades

**When to load:** Snakemake is rerunning a long chain of rules even
though their outputs already exist on disk; or you're configuring a
new workflow profile and want to know which `rerun-triggers` to set.

Default `rerun-triggers` includes `mtime`. With a serial chain
`m1 → m2 → ... → m6`, regenerating m1's archive makes m2 rerun
(m1 is "newer than m2 output"), which makes m3 rerun, etc., even if
m2..m6 archives already exist on disk.

## Fix

In your workflow profile (`profile/config.yaml`):

```yaml
rerun-triggers:
  - input    # rule reruns only if the SET of input paths changes
# DON'T include mtime, params, or code unless you really mean it
```

## Why this is safe

Existence-of-output check still prevents redoing completed rules
through the regular DAG resolution. This narrowly disables the
forward-cascade behaviour only.

If you actually do want to invalidate downstream when an input was
edited, do it explicitly: `snakemake --forcerun <rule>` or
`--cleanup-metadata <file>` on the changed input.
