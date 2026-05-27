# Idempotent resubmission and stale-chunk pitfalls

**When to load:** re-submitting a chained pipeline that crashed
mid-way (or topping up missing pieces), or designing a new chunked
array pipeline that merges per-chunk outputs.

## Check outputs before submitting

Before re-submitting a chained pipeline that crashed mid-way (or you
just want to top-up missing pieces), **audit existing outputs per
(unit, stage) at the granularity downstream consumers need.** Don't
trust a single coarse predicate like "stage M's main output exists"
as a proxy for "stage M is fully done" if downstream needs sub-unit
outputs (per-ROI, per-run, per-event-type).

Two failure modes if you don't:

1. **Duplicate compute** — the same job re-runs against the same
   input, wasting cluster slots and crowding the queue your *new*
   priority jobs need.
2. **Output overwrite races** — two running jobs writing to the
   same file. If they finish near-simultaneously and one has a bug,
   the bad one can clobber a good result. Worse, you might not
   notice for a long time.

Pattern: each pipeline stage gets a `done(unit, stage)` predicate
that checks the **exact** files downstream will read. The submit
script skips submission iff `done(unit, stage)` returns true.

```bash
done_stage() {
    local unit=$1 stage=$2
    case "$stage" in
        prf)   [[ -f "${OUT}/prf/${unit}/result.nii.gz" ]] ;;
        atlas) [[ -f "${OUT}/atlas/${unit}/inferred.mgz" ]] ;;
        af)    # per-(unit, roi) — coarser would lie
               local n=$(ls "${OUT}/af/${unit}/" 2>/dev/null \
                           | grep -oE 'roi-[A-Za-z0-9]+' | sort -u | wc -l)
               [[ "$n" -eq "$N_ROIS_EXPECTED" ]] ;;
    esac
}
```

Downstream blocks should be willing to submit with **no afterok dep**
when their predecessor was skipped (its output is already on disk).
Pass empty job-IDs through dep wiring; build `--dependency=afterok:$X`
only when `$X` is non-empty.

## Stale chunks from previous sweeps

Chunked-then-merged array pipelines write per-chunk files like
`chunks/chunk-NNNN-of-MMMM.npz` and then merge into the final
output. **Pitfall:** re-running with a different `MMMM` (e.g.,
switching from `N_CHUNKS=10` to `N_CHUNKS=40`) leaves orphan chunks
with the old suffix in `chunks/`. The merge script — which usually
parses `MMMM` from the first chunk and counts files vs that total —
silently picks up the wrong total, mis-concatenates, or errors with
`K chunk files found but expected M`. Cascade: merge FAILED →
downstream `afterok` jobs all `DependencyNeverSatisfied`.

### Fixes (any one works; the third is most robust)

```bash
# 1. Wipe chunks/ before resubmit (idempotent restart):
rm -rf "${OUT}/${unit}/chunks/"

# 2. Selective delete: keep only chunks matching the current MMMM:
find "${OUT}/${unit}/chunks" -name 'chunk-*-of-*' \
    ! -name "chunk-*-of-$(printf '%04d' $N_CHUNKS).*" -delete

# 3. Make the merge script glob by the current MMMM, not all:
glob_pattern="chunk-*-of-$(printf '%04d' $N_CHUNKS).npz"
chunks=$(ls "${chunks_dir}/${glob_pattern}")
```

Symptom when you've been bitten: a couple of subjects'/units' merges
fail while others succeed, and the failed ones are exactly the ones
whose `chunks/` dir hadn't been cleared from a previous attempt that
used a different `N_CHUNKS`.
