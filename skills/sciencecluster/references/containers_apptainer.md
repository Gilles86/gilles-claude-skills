# Containers: apptainer (not singularity), and the host-binary reuse hack

**When to load:** writing or fixing a script that runs an fmriprep /
mriqc / qsiprep container, or hitting `module(s) are unknown:
"singularityce"` / `singularity: command not found`. Also when you
need a FreeSurfer / AFNI / etc. binary that isn't in your conda env.

## apptainer, not singularity

Cluster migrated **singularityce → apptainer/1.4.1** (open-source
fork; same CLI, different module name). `.sif` images at
`/shares/<account>/containers/` are unchanged.

```bash
#!/bin/bash -l
module load apptainer
apptainer exec --cleanenv --writable-tmpfs \
    --bind "$CONFIG_FILE:/flywheel/v0/input/config.json" \
    --bind "$OUTPUT_DIR:/flywheel/v0/output" \
    "$SIF_IMAGE" /flywheel/v0/run
```

Symptoms of stale scripts: `Lmod ... module(s) are unknown:
"singularityce"`, or `singularity: command not found` (the
`singularity` name is gone — apptainer doesn't ship a compatibility
symlink). Fix is mechanical: replace `singularityce` → `apptainer`
and `singularity` → `apptainer` everywhere.

## Reusing container-bundled binaries from the host

`/shares/<account>/containers/<image>/` is an *unpacked sandbox*
container (a directory tree, not a `.sif`). The Linux executables
inside are compiled against generic glibc and **run directly from the
host** — no `apptainer exec` needed. This is hacky but well-tested
and useful when you need a tool that's not in your conda env.

Concrete example for this account: `mri_surf2surf` and the rest of
FreeSurfer aren't in our conda envs, but they live inside the fmriprep
container:

```bash
FS_BIN=/shares/zne.uzh/containers/fmriprep-25.2.5/opt/freesurfer/bin
$FS_BIN/mri_surf2surf --version    # works directly
$FS_BIN/recon-all --help

# For nipype's SurfaceTransform (or anything that shells out to
# mri_surf2surf via PATH), prepend the bin dir to PATH:
export PATH=$FS_BIN:$PATH
export FREESURFER_HOME=/shares/zne.uzh/containers/fmriprep-25.2.5/opt/freesurfer
```

The standalone `/shares/zne.uzh/containers/freesurfer/` directory only
holds the license file (`license.txt`) — point `FS_LICENSE` or
`APPTAINERENV_FS_LICENSE` there. The actual FreeSurfer install lives
inside whichever fmriprep image you want (different images ship
different FS versions — the 25.2.5 image has FS 7.3.2).

The alternative is a proper FreeSurfer container with `apptainer exec`;
both work, but the bind-into-PATH hack saves you the container wrapper
overhead for one-off scripts.
