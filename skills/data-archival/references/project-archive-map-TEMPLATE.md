# Project → archive map (TEMPLATE)

Copy this into a **private** note (not this repo) and fill in your own datasets,
repos, and archive locations. The map is what makes "can I delete X?" answerable
in one glance; keeping it private avoids publishing paths, hostnames, PI names,
or account details.

| Local dataset | Active? | Code repo | Remote (e.g. GitHub) | Institutional-share folder | Cluster mirror? |
|---|---|---|---|---|---|
| `…/ds-foo` | yes/no | repo-name | org/repo | `projects/<year>/<short>/data` | yes (size) / NO / only-here |

Guidance:
- **Active?** = currently being worked on → keep the working copy local.
- **Cluster mirror?** Record `yes (size)`, `NO`, or "lives under a non-standard
  path" so future-you knows whether the cluster is a valid restore source.
- Flag datasets that exist **only locally** — those must be archived before any
  deletion.
- Note per-dataset quirks: disposable scratch dirs (`nipype*`, caches),
  superseded `*.bak`/`old/` cruft, nested pipeline outputs (e.g. FreeSurfer
  inside fMRIPrep), uncompressed raw that could be gzipped in place, and
  hand-edited masks/ROIs that are NOT reproducible.
- **Verification standard:** per-file checksum (`rsync -rni -c SRC/ 'DEST/'`,
  while mounted) is the only trusted proof. `du -sh` totals catch gross gaps
  only. See SKILL.md for the flaky-SMB details.
