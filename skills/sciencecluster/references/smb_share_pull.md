# Pulling data from a UZH SMB share straight onto the cluster

Departmental archives (Windows/SMB NAS shares, e.g. `//<nas-host>/<share>$`)
are usually mounted on the workstation and copied share → laptop → cluster.
That hauls every byte over the VPN twice. The login node can talk SMB to the
NAS itself, so pull **directly into `/scratch` or `/shares`** instead.

## What's there

- The login node reaches UZH NAS hosts on port 445, and `smbclient`, `smbget`
  and `rclone` are installed in `/usr/bin` (verified 2026-10).
- Anonymous access lists hosts but cannot read a departmental share; you need
  your UZH identity. **No credentials are stored on the cluster** — the user
  creates a Kerberos ticket per session.

## Recipe

1. **The user** creates a ticket (they type their own password — an agent
   never handles it). From Claude Code:

   ```
   ! ssh -t sciencecluster kinit <uzh-user>
   ```

   Principal is `<uzh-user>@D.UZH.CH`; `klist` confirms. The ticket lasts
   about a day.

2. Check access (cheap, read-only):

   ```bash
   ssh sciencecluster "smbclient --use-kerberos=required '//<nas-host>/<share>\$' \
       -c 'ls projects/<year>/<folder>/data/*'"
   ```

   `-k` is deprecated; with no ticket it fails as
   `session setup failed: NT_STATUS_INVALID_PARAMETER`, which is the
   "kinit first" signal, not a network problem.

3. Pull a directory tree:

   ```bash
   smbclient --use-kerberos=required '//<nas-host>/<share>$' \
       -D 'projects/<year>/<folder>/data' \
       -c 'prompt OFF; recurse ON; lcd /scratch/<user>/<dest>; mget <dir>'
   ```

   For selective pulls (a few runs per subject), loop over explicit
   `get <remote> <local>` commands in one `-c` string rather than `mget`
   of the whole tree.

## Traps

- **The ticket cache lives in `/tmp/krb5cc_<uid>` on the login node you ran
  `kinit` on.** Compute nodes don't see it, and there are several login nodes
  (`u24-login-*`); an ssh that lands on another one has no ticket. Either run
  the pull on the login node (fine for a few GB: it's network-bound, not CPU),
  or `kinit -c /scratch/<user>/krb5cc` and `export KRB5CCNAME=/scratch/<user>/krb5cc`
  in the job script so a SLURM job can use it.
- **Departmental archives are typically append-only.** Use only `ls`, `get`,
  `mget`. Never `put`, `del`, `rm`, `rmdir`, `rename` against the share.
- Quote the literal `$` in the share name (`'...$'` or `\$` inside double
  quotes), same as on the Mac mount.
- SMB doesn't preserve mtimes, so verify a pull with checksums
  (`md5sum` on both sides via `smbclient -c 'get … -'` piped, or compare
  against a workstation-side `rsync -c` run), not sizes and dates.
