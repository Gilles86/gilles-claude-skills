# What to put in a project's CLAUDE.md

Hand-curated, not auto-generated.

## Required sections

1. **One-line pitch** — paradigm, N, scanner
2. **Paths** — local + cluster BIDS roots, sourcedata, derivatives
3. **Subject naming** — pilot vs study, zero-padding, exclusions
4. **Environment setup** — env names, build commands, known
   incomplete envs on cluster
5. **Pipeline stages** in order, with file paths and one-line
   descriptions
6. **CLI examples** — copy-paste-runnable commands for common
   analyses
7. **SLURM examples** — typical array submissions
8. **Per-subject gotchas** — pilot quirks, bugged runs, missing
   sessions

## Optional (add as the project grows)

9. **Model label table** — when there are multiple model variants;
   note where the dispatch lives if scattered across scripts
10. **Experimental constants** — TR, volumes per run, stimulus
    geometry (read from per-run yml when possible, don't hardcode)
11. **Subject QC ranking** — when there's variation in fit quality
    that affects exclusion/demo decisions
12. **Plotting conventions** — FWHM vs σ, label conventions, etc.

## Starting point

Skeleton to copy: [CLAUDE.md.template](CLAUDE.md.template).
retsupp's CLAUDE.md (~300 lines) is the most fleshed-out reference in
the wild.
