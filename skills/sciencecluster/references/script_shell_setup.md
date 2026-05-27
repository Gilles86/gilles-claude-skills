# Inside the SLURM script: `#!/bin/bash -l` and `module`

**When to load:** writing a SLURM script that calls `module load …`, or
debugging a job that errors with `module: command not found` /
`command not found` for something that should be there.

## Use `#!/bin/bash -l`

Plain `#!/bin/bash` SLURM scripts run as non-login non-interactive
bash and source nothing — `module` isn't defined, `MODULEPATH` is
empty. Use `#!/bin/bash -l` to make the script a login shell so
`/etc/profile` → `/etc/profile.d/*.sh` get sourced and `module`
works:

```bash
#!/bin/bash -l
module load apptainer
```

## The silent-failure variant

A `#!/bin/bash` script that does `. "$HOME/.bashrc"` thinking that
fixes it. `.bashrc` starts with the standard

```bash
case $- in *i*) ;; *) return ;; esac
```

guard and returns early non-interactively — its body never runs, and
downstream `module load X` fails. Without `set -e` the script keeps
going and the missing tool fails later as `command not found`. This
pattern sabotaged a lot of old scripts.

## Alternatives

`source /etc/profile` works too (explicit; same chain). Don't
`source /etc/profile.d/lmod.sh` alone — it defines `module` but
leaves `MODULEPATH` empty.
