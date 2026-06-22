---
name: data-archival
description: Reclaim local disk by safely archiving and deleting large research datasets (e.g. fMRI/BIDS working copies) across a two-tier backup setup — a compute cluster as canonical big-data archive plus an institutional SMB share as the official per-project archive. Covers verify-before-delete with checksums, the macOS openrsync + flaky-SMB-mount pitfalls, and a safe audit→back-up→delete workflow. Use whenever local disk is full or filling, when asked to "back up", "archive", "free space", "clean up data", "can I delete this dataset", or "is X backed up". Personal project→archive maps belong in your own private notes, not here.
---

# Data archival & disk cleanup

A playbook for backing up essential research data and deleting reproducible data
safely, when a workstation holds large working copies of datasets that also live
on backup tiers. Written around fMRI/BIDS datasets on macOS, but the pattern
generalizes.

> **Personalize, don't commit personal data here.** Keep your own map of
> "which dataset → which repo → which archive location" in a *private* note
> (e.g. `~/.claude/reference/…` or your private global instructions). This skill
> is the shareable method; it deliberately contains no specific paths,
> hostnames, project names, or accounts.

## Treat local data as a WORKING COPY, not the master

Large dataset trees on a workstation are working copies. Identify the backing
tiers before deleting anything:

1. **Compute cluster / group storage** (e.g. an HPC `/shares/<group>/…` over
   `ssh`) — usually the **canonical, largest archive**; the cluster copy is
   often more complete than local. Confirm a dataset is here before deleting the
   local copy of reproducible data.
2. **Institutional / departmental share** (e.g. an SMB volume under
   `/Volumes/<share>`) — the **official per-project archive** for essential
   raw/behavioral/key-results data, and the home for datasets that aren't on the
   cluster.

A dataset may live on one, both, or neither. The deletion decision depends on
*which*.

## HARD RULES
- **Never delete without the owner's explicit, per-item approval.** Produce the
  exact `rm` commands; let them run them.
- **Treat the institutional archive as append-only** — never delete from it.
- Before clearing a local dataset, confirm it is either (a) mirrored on the
  cluster, or (b) checksum-verified-copied to the institutional share.
- **Reproducible** (pipeline `derivatives/` — fMRIPrep/FreeSurfer/GLM/PRF fits,
  `nipype*`/scratch working dirs, caches) → deletable once mirrored.
  **Essential** (raw BIDS, behavioral/events, sourcedata, non-regenerable fits,
  published-results bundles, hand-edited masks/ROIs) → keep / archive.

## macOS SMB + openrsync — the pitfalls
- macOS ships only Apple's `openrsync` (protocol 29): it **rejects**
  `--log-file`, `--info=progress2`, and `-a` permission flags choke on SMB ACLs.
  Working, resumable command:
  ```bash
  rsync -rt --modify-window=2 --partial SRC/ 'DEST/'   # single-quote any literal $ in the path
  ```
- **Institutional SMB mounts can drop mid-operation.** Symptoms: rsync
  `error: unexpected end of file`; `du`/`ls`/`stat` on share paths return "No
  such file or directory"; a dry-run suddenly flags *every* file (even
  top-level dirs, `cd+++++++ ./`) as needing transfer. That usually means **the
  share dismounted, NOT data loss.**
  - Check before trusting anything: `mount | grep -i <share>` (empty = gone),
    then remount (`open "smb://…"`, needs credentials).
  - **Serialize** transfers (one at a time) and **retry** on drop
    (`for i in 1 2 3; do rsync … && break; sleep 5; done` — `--partial` resumes).
  - **Verify ONLY with checksums while mounted:** `rsync -rni -c SRC/ 'DEST/'`.
    A plain size+mtime check is useless over SMB — mtimes are never preserved, so
    every file shows `>f..T....` even when byte-identical. With `-c`,
    content-identical files show a leading `.`; only genuine diffs/missing show a
    leading `>` (filter with `grep -E '^>f'`). A clean `-c` run is real proof; a
    "missing" result is suspect until the mount is re-confirmed.
  - A checksum match made while mounted stays valid even if the share later
    drops — don't re-doubt already-verified items.
- **`du -sh` is a coarse check only.** It catches gross gaps (a whole missing
  subtree) but not a single missing/truncated file when totals happen to match.
  For anything irreplaceable, use the `-c` checksum verify.

## Verify-then-delete workflow
1. **Audit local**: `du -sh DATASET/*/`, drill into `derivatives/`. Classify
   essential vs reproducible (check the project code for which derivatives the
   live analysis actually reads).
2. **Locate the archive**: check the cluster (`ssh … du -sh …`) and/or the
   institutional share (checksum, while mounted). Larger-on-archive is fine
   (local is usually a subset); the real danger is files that exist *only*
   locally — those must be archived first.
3. **Back up** local-only data to the archive (append-only), then
   **checksum-verify** it.
4. **Hand over exact `rm -rf` commands**, grouped "already mirrored → delete now"
   vs "after backup verified". The owner runs them.

## Agent-sandbox caveat (Claude Code subagents)
Subagents are typically sandboxed to the working dir: they can read local data
but are often **denied `ssh`, other mounts (`/Volumes/...`), and `~`-level repo
dirs**. So per-project audit agents do the **local breakdown** well, but the
**archive-mirror verification must run in the main session**. Don't make a
sandboxed agent the verifier.

## Other common workstation space hogs
- Conda/mamba: prune `.bak`/`_backup`/`_test` envs (`conda env remove -n …`) +
  `conda clean -a`.
- Downloads: `find ~/Downloads -mindepth 1 -maxdepth 1 -mtime +28 -exec rm -rf {} +`
  (preview with `-print` first).
- Subject surface DBs (pycortex/FreeSurfer `SUBJECTS_DIR`): large but usually
  keep.
- Cloud-drive (e.g. rclone): stream uploads directly (`rclone copy SRC remote:… -P`)
  rather than staging into a synced folder when local disk is tight; never delete
  local until the upload is confirmed.

See `references/project-archive-map-TEMPLATE.md` for a blank map to copy into
your private notes.
