# fmriprep references

Copy-pasteable artifacts for the lessons in `../SKILL.md`. Each file uses
`<project>` (BIDS dataset short name, e.g. `abstractvalue`), `<package>`
(the Python package, e.g. `abstract_values`), and `<version>` (apptainer
image tag) as placeholders — replace before use.

| File | Goes to | Purpose |
|------|---------|---------|
| `fmriprep.sh` | `<package>/cluster_preproc/fmriprep.sh` | The wrapper SLURM script — apptainer invocation, BIDS filter, `--bold2anat-init` passthrough, the **output-based** (not HTML-based) exit-code discriminator, and the `.fmriprep_done` completion sentinel. |
| `clean_rerun.md` | — | The 3-path cache wipe, runtime smell-test table, and "is it real?" post-run checklist. The fix for the cache trap and the silent-`--bold2anat-init` bug. |
| `check_coreg.py` | `<package>/visualize/check_coreg.py` | Batch coregistration QA — boldref edges over T1w (nilearn `add_edges`), one PDF per subject. |
| `inspect_coreg_fsleyes.py` | `<package>/visualize/inspect_coreg_fsleyes.py` | Interactive coregistration QA — loops fsleyes over (subject, session), close-window-to-advance. |
