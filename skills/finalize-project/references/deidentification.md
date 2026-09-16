# De-identification beyond faces

Faces are the obvious identifier. The rest hide in filenames, headers, logs
and free-text fields written by converters and pipelines you never looked at.
Audit the whole upload tree mechanically; then read the remaining free text
yourself.

## Where identifiers hide

| Where | What | Fix |
|---|---|---|
| Directory / file names | pilot folders named after people (`sub-<firstname>`), zips, initials in `sourcedata/`, dates in session labels | exclude pilots; rename or drop |
| `participants.tsv` | `participant_id` as bare numbers (must be `sub-XX`); exact age (consider binning); never birthdate or scan date | rewrite; `participants.json` describes columns |
| `*_scans.tsv` | `acq_time` = real date | drop the column, or shift all dates consistently (BIDS allows) |
| Physio logs (Philips/Siemens raw) | header lines with scan date/time, sometimes patient fields | convert to BIDS `_physio.tsv.gz` + JSON (headers gone) or strip lines |
| Eye-tracking `.edf` / `.asc` | recording date/time in the header; operator strings | convert and strip; or don't share |
| Task logs (PsychoPy/exptools2) | `_log.txt` timestamps + machine paths, `_expsettings.yml` operator/paths, `_frames.pdf` | share only the per-run events TSV the analysis reads |
| NIfTI-1 header text | `descrip`, `aux_file`, `db_name`, `intent_name` — converter version, scanner/server paths, dates, occasionally IDs | blank them (byte-level header rewrite; voxels and scaling untouched) |
| NIfTI gzip wrapper | original filename + mtime embedded by `gzip` | `gzip -n`, or write via Python `gzip` with `mtime=0` |
| JSON sidecars | `AcquisitionTime`, `AcquisitionDateTime`, `PatientName/ID/BirthDate/Sex/Weight`, `InstitutionAddress`, `DeviceSerialNumber`, `StationName`, `ProcedureStepDescription`, `SeriesInstanceUID`, `ImageComments` | key inventory across all JSONs; drop by denylist; keep acquisition parameters |
| `dataset_description.json` | stale `Name` from a different study, wrong licence boilerplate | rewrite from scratch |
| FreeSurfer | `surf/*` file headers "created by <user> on <date> <host>"; `scripts/recon-all.{log,cmd,env,done}`, `build-stamp.txt`; `stats/*.stats` headers (`# user`, `# hostname`, `# cmdline`, `# SUBJECTS_DIR`, timestamps); `mri/transforms/*.xfm` path comments | drop `scripts/` and `stats/` headers or the whole dirs; accept surface stamps or rewrite |
| fMRIPrep | `sub-XX.html` (full command line, work dir, hostname), `logs/`, `*.toml`, `figures/*.svg` | drop reports and logs; keep NIfTI/GIfTI/TSV/JSON outputs |
| Model derivatives | JSON manifests with hostnames/paths/usernames; pickles with absolute paths | strip manifests to versions + commit SHAs; never ship pickles |
| macOS / editors | `.DS_Store`, `._*` AppleDouble, `.ipynb_checkpoints`, `__pycache__` | delete; `.bidsignore` is not enough — they still upload |
| `README` / `CHANGES` | operator names, internal project codes | read them |

## Whole-tree audit — mechanical first

Template: [`identifier_audit.py`](identifier_audit.py). What it does, and
why each step exists:

1. **File-type allowlist.** Every file must be one of the expected kinds
   (`.nii.gz`, `.json`, `.tsv`, `.tsv.gz`, `README`, `CHANGES`, `.bidsignore`,
   `.bvec/.bval`, GIfTI, `.mgz`, …). Anything else is a finding: a stray zip,
   a `.DS_Store`, a PDF, a notebook.
2. **Regex scan of text files** for: a private **name list** (participants,
   operators, colleagues, PI — kept outside the repo), dates in common
   formats (`2024-04-15`, `15-04-2024`, `15 Apr 2024`, `Mon 15-04-2024`),
   times, e-mail addresses, absolute paths (`/Users/`, `/home/`, `/data/`,
   `/shares/`, `/scratch/`, `C:\`), hostnames (`.<institution-domain>`,
   `.local`), IPv4 literals.
3. **Printable-string scan of binaries.** gunzip in memory; extract printable
   runs ≥ 6 chars from the first N MB (headers, extensions, MGZ tags live at
   the start or end — scan both ends); apply the same regexes. For NIfTI also
   read the four text fields explicitly with nibabel and require them empty.
4. **JSON key inventory.** The set of all keys across all sidecars is small
   (< 100). Print it once, read it, denylist what must go.
5. **High-res 3D volume listing.** Every NIfTI/MGZ with 3 spatial dims and
   voxel size < 1.5 mm must appear in `qc_approved.tsv` (defacing gate) or
   pass the outside-brain check (skull-stripped derivative). This catches a
   mis-named or forgotten anatomical regardless of its filename.
6. **Output** a TSV of findings (`path, kind, pattern, match, context`).
   Clean = zero rows. Run on `TARGET` right before upload; rerun after any
   change to the tree.

Then the non-mechanical part: open `README`, `CHANGES`,
`dataset_description.json`, `participants.json`, the events JSON and one
example of every sidecar type, and read them.

## `sourcedata/` policy

Share only what the analysis code reads to reproduce the paper — typically
the per-run behavioural events the analysis code loads — after header
stripping. Drop pilots, free-text logs, PDFs, zips, screenshots. If the
release rebuilds BIDS `events.tsv` from those raw logs, have the staging
script **assert equality with the events the analyses used** (onsets,
stimulus values, responses) — this both documents provenance and proves the
shared files support the paper.

## Demographics

`age` and `sex` are what most papers report and what OpenNeuro expects in
`participants.tsv`. Decide explicitly (with the consent form in hand) whether
to share exact age or bins; put the decision in the dataset `README`. Never
share anything not in the paper's Methods.
