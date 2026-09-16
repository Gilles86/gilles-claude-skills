# OpenNeuro release

Raw BIDS (+ optionally the derivatives the paper used) on OpenNeuro, private
until publication, snapshot → DOI. Everything happens on a **staging copy**;
the canonical dataset is never touched.

## 0. Decide scope first

Write the decisions down before staging (they change filenames):

- **Subjects**: the analysed sample with original IDs (matches code, the
  analysis's subject table, derivatives). Pilots out. Excluded-but-scanned subjects: in
  with a README note, or out — pick and document.
- **Modalities**: BOLD + fieldmaps + T1w (+ T2w) yes. Physio, eye-tracking,
  raw behavioural logs: only if the paper uses them or you commit to
  de-identifying them (see `deidentification.md`).
- **Snapshots**: v1.0.0 = raw BIDS (fast, gets the DOI for the paper);
  v1.1.0 = curated derivatives later. Or both at once if they're ready.
- **Task label**: renaming `task-task` → `task-<meaningful>` is cleaner but
  renames every derivative filename and every JSON `Sources`/`IntendedFor`
  that mentions it, and the code's path builders. If you rename, do it in the
  staging script via one `rename_task()` helper used everywhere.

## 1. Stage (cluster; never edit canonical)

```bash
SOURCE=<canonical-dataset>            # read-only
TARGET=<canonical-dataset>-openneuro  # upload tree
WORK=<canonical-dataset>-openneuro-work   # undefaced anatomicals, masks, QC; never uploaded
```

Release code lives in a `data_release/` folder of the repo, one script per
step (any language) so each is re-runnable per subject and every gate is
explicit:

| Script | Does |
|---|---|
| `release` (shared module) | `SOURCE/TARGET/WORK` constants, released-subject list (from the analysis's own subject table), task rename helper, byte-level NIfTI copy + verify |
| `stage_raw <sub>` | BOLD/fmaps → TARGET; T1w → WORK/undefaced; events rebuilt + checked |
| `stage_derivatives <sub>` | the derivative subset the paper uses; face-bearing volumes → WORK |
| `deface_subject <sub>` | pydeface in WORK; mask applied byte-wise; verify |
| `qc_subject <sub>` / `make_qc_report` | metrics + PNGs; HTML index; reads/writes `qc_approved.tsv` |
| `write_metadata` | top-level JSON/TSV/README/CHANGES/.bidsignore |
| `audit_release` | identifier audit + hi-res-volume guard over TARGET |
| `export_behavior` | the figshare table + codebook |
| `jobs/` | cluster array wrappers for the per-subject scripts |

The byte-level NIfTI copy/verify and the mask application are easiest in
Python (`deface_apply_qc.py` needs only nibabel and works from any lab's
tree); the rest can be MATLAB, R or shell.

Prefer a **per-subject staging script** (`stage_raw 01`, one subject per
cluster job) over one big rsync: it can clean NIfTI header text, gzip
(`.nii` → `.nii.gz` halves the size; use byte-level copy or `gzip -n` so
voxels stay identical and no filename/mtime leaks into the gzip header),
rename the task, rewrite sidecars from an allowlist, rebuild `events.tsv`
with the required `duration`, verify every copied image against its source
(`shape, dtype, qform, sform, scl_slope/inter, voxels`), and send T1w to
`WORK/undefaced/` instead of `TARGET`. Idempotent: re-running overwrites.

Top-level files written once by a separate step: `dataset_description.json`,
`README`, `CHANGES`, `participants.tsv` + `participants.json`,
`task-<label>_bold.json` (inheritance), `task-<label>_events.json`,
`.bidsignore`, `T1w.json` (inheritance) if the raw T1w had no sidecars.

## 2. BIDS fixes seen in practice

| Validator complaint | Cause | Fix |
|---|---|---|
| `INTENDED_FOR` | path wrong (`…_epi_bold.nii.gz`), or relative to the wrong root | BIDS URI: `"bids::sub-01/ses-1/func/sub-01_ses-1_task-x_run-1_bold.nii.gz"`; regenerate from the actual BOLD filenames, don't string-edit |
| `REPETITION_TIME_MISMATCH` | NIfTI `xyzt_units` says `msec` while pixdim[4] is in seconds — the TR *values* were right | `hdr.set_xyzt_units(spatial, 'sec')`; then set JSON `RepetitionTime` to `float(pixdim[4])` exactly |
| TR differs between README, JSON and header | three sources of truth | header pixdim is what fMRIPrep used; make JSON match it; fix README |
| `duration` missing / `n/a` in events | converter never wrote it | rebuild events from the task logs with real durations; `n/a` for missing values, never empty |
| `participant_id` not `sub-XX` | bare numbers | rewrite; add `participants.json` |
| `TaskName` missing / non-standard key (`"task"`) | old converter | top-level `task-<label>_bold.json` with `TaskName`, `TaskDescription`; delete non-standard keys |
| Licence must be CC0 | OpenNeuro requirement | `"License": "CC0"` in `dataset_description.json` |
| Stale `dataset_description.json` | copied from another study | rewrite: `Name` (paper title), `BIDSVersion` (current), `DatasetType: raw`, `Authors`, `Funding`, `EthicsApprovals`, `ReferencesAndLinks` (paper DOI, GitHub, Zenodo, figshare), `HowToAcknowledge`, later `DatasetDOI` |
| Missing `EchoTime`, `FlipAngle`, `MagneticFieldStrength`, `Manufacturer` | PAR/REC or old dcm2niix | add from the protocol PDF; **seconds**, not ms |
| macOS `._*`, `.DS_Store` | Finder | delete before validating; `.bidsignore` does not stop the upload |
| Non-BIDS files you keep on purpose | raw physio, stimulus files | list in `.bidsignore`; document in README |
| Warnings about `sourcedata/` | not validated | fine if de-identified; or `.bidsignore` it |

Validate until **zero errors** (warnings: read them, fix the cheap ones):

```bash
deno run -A jsr:@bids/validator "$TARGET"                 # deno ≥ 2; no install step
deno run -A jsr:@bids/validator "$TARGET" --json > validator.json   # machine-readable
```

## 3. De-identify + deface (gates)

[`deidentification.md`](deidentification.md) for the tree audit,
[`defacing.md`](defacing.md) for the anatomicals. Both must be clean on
`TARGET` before the upload. The defaced T1w enter `TARGET` only from the
QC-approved list.

## 4. Upload (private), inspect, snapshot

```bash
deno run -A jsr:@openneuro/cli login          # paste API key from openneuro.org → My Account → Obtain an API key
deno run -A jsr:@openneuro/cli upload "$TARGET"                       # creates a new dataset; prints ds00XXXX
deno run -A jsr:@openneuro/cli upload --dataset ds00XXXX "$TARGET"    # subsequent uploads / additions
```

Upload from wherever the staging tree is (deno runs on the cluster too; a
login node is fine for I/O — or rsync `TARGET` to a workstation first).

Then, in the web UI:
1. The dataset is **private** by default. Keep it so until publication. Add
   co-authors as admins; reviewers can be added as read-only collaborators
   (there is no anonymous link).
2. Open several T1w in the viewer — confirm the defaced images are what
   arrived. Check the file count against `find "$TARGET" -type f | wc -l`.
3. OpenNeuro re-runs the validator server-side; it must be green.
4. **Create snapshot 1.0.0** → DOI `10.18112/openneuro.ds00XXXX.v1.0.0`.
   Snapshots are immutable; fixes become 1.0.1. Write the CHANGES entry first.
5. At publication: **Publish** (makes it public). The DOI existed since the
   snapshot, so the paper can cite it before.

Download one subject from the published snapshot afterwards and checksum it
against `TARGET` — the round trip is the final proof.

## 5. Derivatives (if shipped)

Include **only what the paper's figures/statistics read** — the production
chain, not every sweep. Typical: preprocessed BOLD (T1w space) + brain masks
+ confounds, single-trial betas, ROI masks, the production model's parameter
maps, decoded PDFs. Not: MNI-space or fsaverage outputs nobody used,
alternative-configuration sweeps, work dirs, reports/logs (identifiers).

- Face-bearing derivatives: `desc-preproc_T1w` defaced with the same QC gate
  (or dropped), FreeSurfer full-head volumes dropped (allowlist +
  outside-brain check), MRIQC/fMRIPrep reports dropped.
- `derivatives/<pipeline>/dataset_description.json` with
  `"DatasetType": "derivative"`, `GeneratedBy` (one entry per tool: `Name`,
  `Version`, `CodeURL`, `Description`; the project code with its commit/tag;
  the in-house library with its commit), and `SourceDatasets`
  (`{"URL": "https://openneuro.org/datasets/ds00XXXX", "Version": "1.0.0", "DOI": "..."}`).
- Renamed task label ⇒ rename derivative filenames **and** the `Sources`
  fields in derivative JSONs; the staging helper does both.
- OpenNeuro hosts derivatives inside the same dataset (`derivatives/`
  folder, `.bidsignore` if the validator objects) or as a linked derivative
  dataset; either way a new snapshot (1.1.0).

## 6. Wire up

Dataset `README` mentions the paper, the GitHub repo and the code DOI;
`dataset_description.json` `ReferencesAndLinks` lists all of them; the
project README and the paper's Data Availability carry the OpenNeuro DOI.
