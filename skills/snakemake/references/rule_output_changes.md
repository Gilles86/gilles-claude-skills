# Changing a rule's `output:` sentinel — backfill FIRST

**When to load:** about to change the `output:` path of a Snakemake rule
in an active project — e.g. swapping a sentinel from one file to
another, renaming a derivative dir, adding/removing a smooth-suffix
component. Especially critical when the rule is **expensive**
(fmriprep, GLMsingle, anything taking >30 min per wildcard).

**TL;DR:** every existing wildcard combination whose **new** output
sentinel is missing will be re-dispatched on the next driver tick. For
a 14-subject fmriprep cohort, that's 14 × ~5h = 70 hours of redundant
cluster compute. Backfill the new sentinel for already-complete
wildcards **before** committing the rule change.

## The failure mode

Snakemake's DAG resolver checks `output exists`, not `output equivalent
exists`. The moment a rule's `output:` path changes, Snakemake stops
treating any previously-completed wildcard as done — because the file
*at the new path* doesn't exist for any of them.

With `rerun-triggers: [input]`, mtime cascades from upstream are
suppressed — but missing-output forces a re-run regardless. The
rerun-triggers config doesn't help here.

Result: the driver dispatches the rule for **every** wildcard. If the
rule is fmriprep at 5h × 14 subjects, you've just queued 70 hours of
work that does nothing new (fmriprep is idempotent enough that it
re-produces the same outputs over the existing files, then "fails"
at the end if it has any spurious exit code, marking each rule failed
even though the data is fine).

## Concrete incident — abstract_values, 2026-05-29

Wanted to switch the fmriprep rule's `output:` from `sub-<XX>.html`
(which fmriprep can write mid-run / on failure) to a robust
`sub-<XX>/.fmriprep_done` touch sentinel. Committed the change, pushed,
restarted the driver. The driver:

1. Scanned 14 subjects, found 0 with `.fmriprep_done`.
2. Dispatched fmriprep for all 14 (including the 6 fully-complete
   established subjects).
3. Each ran ~5h, producing the same outputs that already existed.
4. Apptainer exited 1 spuriously on most (a known fmriprep 25.x quirk),
   the wrapper's strict mode failed each, no `.fmriprep_done` touched.
5. Driver died after 5h31m wall, having burned ~70 CPU-hours and
   producing no advance toward the goal.

Avoidable: backfilling 13 × `touch .fmriprep_done` (one ssh, 13 ls
+ touch) before the rule-change commit would have skipped the entire
re-dispatch.

## The pattern

For any rule-output change:

```bash
# 1. Identify already-complete wildcards (real output files exist).
ssh <cluster> "for SUB in 03 04 05 06 07 08 09 10 13 14 pil01 pil02; do
    OLD_SENT=/shares/.../old_sentinel_path/sub-\$SUB...
    NEW_SENT=/shares/.../new_sentinel_path/sub-\$SUB/.<rule>_done
    # Witness: pick a late-stage output file that proves the rule
    # actually completed (NOT the sentinel — that would be circular).
    WITNESS=/shares/.../derivatives/.../sub-\$SUB_..._desc-late_stage_output.nii.gz
    if [ -f \"\$WITNESS\" ]; then
        mkdir -p \"\$(dirname \"\$NEW_SENT\")\"
        touch \"\$NEW_SENT\"
        echo \"backfilled sub-\$SUB\"
    fi
done"

# 2. THEN edit the Snakefile output: line, commit, push.
# 3. THEN restart the driver. It'll only run the rule for wildcards
#    where the witness is genuinely missing.
```

For a project with many such rules (abstract_values has 24 in its
Snakefile), it's worth writing a project-level `backfill_sentinels.py`
that maps each rule's old → new sentinel path + a per-rule witness
check. abstract_values has one at
`abstract_values/snakemake/backfill_sentinels.py`.

## Smell test before committing

Before you commit a rule-output change, run:

```bash
ssh <cluster> "ls <new_sentinel_glob>"
```

If the result is empty (or very short relative to the cohort size),
you have not backfilled. Stop, write the backfill, run it, then commit.

## Compounding hazard

This rule applies to **all** Snakemake rule output changes, not just
sentinels. Renaming a derivative dir (e.g. `derivatives/decoding/value` →
`derivatives/decoded_value`), adding a wildcard component (e.g.
`{smooth}` to a previously single-variant rule), or splitting one rule
into two — all of these cause the same total-cohort re-dispatch
pathology unless the new outputs are backfilled to match the old ones.

## See also

- [`orphaned_jobs.md`](orphaned_jobs.md) — the *other* way a Snakemake
  cohort run gets into a 70-hour-of-wasted-compute state.
  Different cause (driver-restart with preserved jobs); same symptom
  (mass re-dispatch + scratch racing).
- [`rerun_triggers.md`](rerun_triggers.md) — the mtime-cascade variant
  of the same problem family.
