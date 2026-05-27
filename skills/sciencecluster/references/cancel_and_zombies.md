# Cancelling chains and sweeping `DependencyNeverSatisfied` zombies

**When to load:** a chain broke and you need to cancel everything
downstream from an old broken submission wave, or `squeue` is full of
PD jobs with `Reason=DependencyNeverSatisfied`.

## Cancel by JobID range, not by name

When a chain breaks and you want to cancel everything downstream from
an old broken submission, **filter by parent JobID range, not
job-name substring.** Many job classes (especially aggregator /
analysis stages) are named generically across all subjects (e.g.,
`fit_attention_model`, `dog_dyn_target_shS`, `prf_merge`); a
"contains sub-13" filter misses them and leaves orphans that generate
fresh `DependencyNeverSatisfied` waves an hour later.

```bash
# Cancel any of my PENDING jobs whose parent JobID falls in a range
# (typically: "everything from the broken pre-fix submission wave"):
squeue --me -t PD -h -o '%i' \
    | awk -F_ '{print $1}' | sort -u \
    | awk -v lo=3019000 -v hi=3022000 '$1 >= lo && $1 < hi' \
    | xargs -r scancel
```

The JobID monotone-increases per submission; pick a cutoff right
after your fix landed, cancel everything below it, resubmit.

## Sweeping `DependencyNeverSatisfied` zombies

When an upstream task fails, downstream `afterok` jobs become
permanent zombies. They don't dispatch and don't auto-clean. Find
and cancel them:

```bash
zombies=$(squeue --me -h -t PD --format='%i %r' \
            | grep DependencyNeverSatisfied \
            | awk '{print $1}' \
            | awk -F_ '{print $1}' \
            | sort -u)
[ -n "$zombies" ] && scancel $zombies
```
