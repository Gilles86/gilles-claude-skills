# Mid-flight partition swap with `scontrol update`

**When to load:** your jobs are sitting in PD with `Reason=Priority`
on a busy partition while sibling partitions (like `lowprio`, same
hardware) have idle nodes, and you don't want to cancel and resubmit
because it would break `afterok` chains.

When fairshare throttles jobs on a busy partition (`Reason=Priority`
despite idle nodes on a sibling like `lowprio` that uses the same
hardware), don't cancel and resubmit — you'd break `afterok` chains.
Instead, **rewrite the partition on pending jobs in place**:

```bash
for jid in $(squeue --me -t PD -h -o '%i' \
             | awk -F_ '/^[0-9]+/ {print $1}' | sort -u); do
    scontrol update jobid=$jid Partition=lowprio Account=<new-account>
done
```

## Properties

- Works on **pending jobs only**. Running jobs keep their current
  partition.
- **JobIDs are preserved**, so every `afterok:$JID` downstream still
  points at the right parent — the dep graph is unchanged.
- Can also update `Account=` in the same command. Useful when you
  notice mid-flight that you've been submitting under a legacy
  account.
- Effect is immediate: re-dispatch typically lands within ~30 s if
  the new partition has free slots.

## Cost

The usual `lowprio` (or whichever sibling you move to) trade-off —
typically lower job priority and/or preempt risk. Worth checking the
destination partition's preempt policy before mass-moving
critical-path work.
