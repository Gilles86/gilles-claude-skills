# Environment reproducibility (Python, R, MATLAB)

Two layers per environment, always: a **human-readable spec** someone builds
an env from, and a **byte-level lock** that records what actually ran. The
spec is for the stranger; the lock is the evidence. What "spec" and "lock"
mean differs by language:

| Language | Spec (what you tell people to build) | Lock (what actually ran; commit it) |
|---|---|---|
| Python | `environment.yml` (conda) or `requirements.txt` with `==` pins | `conda env export > environments/<platform>_<env>.lock.yml`; `conda list --explicit > ….explicit.txt`; or `pip freeze` |
| R | `renv.lock` (+ `DESCRIPTION` if the project is a package) | `renv::snapshot()`; `sessionInfo()` saved to `environments/sessionInfo_<platform>.txt` |
| MATLAB | MATLAB release (e.g. R2023b), required toolboxes, external toolboxes (SPM, FieldTrip, Psychtoolbox, EEGLAB) with version **and git commit**, and a `setup_paths.m` that adds exactly those | `ver` output saved to `environments/matlab_ver_<platform>.txt`; `spm('Ver')`, `ft_version`; `SPM.SPMid` inside every `SPM.mat` |
| Julia | `Project.toml` | `Manifest.toml` |

Name them by platform when more than one machine produced results:

| File | Ran |
|---|---|
| `environment.yml` / `renv.lock` / `setup_paths.m` | cluster: all fits, GLMs, decoding (environment of record) |
| `environment_<local>.yml`, `environments/matlab_ver_local.txt` | local machine: figures, notebooks, small simulations |
| `data_release/environment_deface.yml` | release-only tooling (pydeface, FSL flirt) — not needed to reproduce the paper |

Pin every version to what the lock says. Comments in the spec say *which*
results this env produced and where the lock is.

Gotchas:
- A stage that ran in a different env than the rest (e.g. GLMs in a MATLAB/SPM
  env, fits in Python): declare it anyway (its own spec + lock) and say so in
  the README. Don't pretend one env did everything.
- Pinning a branch (`@main`, `@develop`) or "SPM12" without the revision number
  is **not a pin**. Commit SHA / revision only.
- MATLAB releases cannot be pinned from a file. Record the release and the
  toolbox list; a Docker image (MathWorks `mathworks/matlab` + MPM) is the
  only way to freeze it, and needs a licence at run time.

## Lock exports, taken on the machine that ran the results

```bash
# Python, ON THE CLUSTER (a login node is fine for this)
conda env export -n <env> > environments/cluster_<env>.lock.yml
conda list -n <env> --explicit > environments/cluster_<env>.explicit.txt   # exact URLs; same-platform recreate
# R
Rscript -e 'renv::snapshot(); writeLines(capture.output(sessionInfo()), "environments/sessionInfo_cluster.txt")'
# MATLAB
matlab -batch "diary('environments/matlab_ver_cluster.txt'); ver; which -all spm; diary off"
```

Commit them with the **export date** in the README ("exported 2026-08-10 from
the environments in which the production fits and figures were run"). The
lock records the env *as it is now*; if anything was upgraded since the fits,
say so.

## Reconstructing pins you never recorded

You will discover an env has been rebuilt or the fits predate the lock. In
order of trustworthiness:

1. Export **now**, before installing anything else into it.
2. Package-manager history: `conda list --revisions`, `conda env export
   --from-history`, `renv` history, MATLAB installer logs.
3. Versions echoed in job logs (`print(tf.__version__)`, `ver` at script
   start, `fmriprep --version`).
4. Artifact metadata: `SPM.mat` (`SPM.SPMid` = SPM version + revision, plus
   every design choice), MCMC trace attributes (bauer stamps its commit into
   `trace.posterior.attrs`), fit manifests with git SHAs.
5. Derivative `dataset_description.json` `GeneratedBy` (fMRIPrep, MRIQC).
6. `git log` of the spec files around the fit dates.
7. Package release dates vs fit dates as an upper bound — last resort, say so.

## Pinning the in-house libraries

Any library the lab wrote itself — a Python package, a MATLAB toolbox in a
git repo, an R package — pinned to the **commit SHA that produced the
published fits**, recorded in four places that must agree:

1. **The spec**:
   - Python: `- "<lib> @ git+https://github.com/<org>/<lib>.git@<full-sha>"`,
     e.g. `"braincoder @ git+https://github.com/Gilles86/braincoder.git@ed48b10ab8cfbba317dafc4e513e5bf23a84c802"`
   - R: `remotes::install_github("<org>/<lib>@<sha>")`, which `renv.lock`
     records as `RemoteSha`
   - MATLAB: the toolbox as a git submodule under `libs/<lib>` at that SHA,
     and `setup_paths.m` adds *that* folder — nothing else on the path
2. **The submodule / vendored copy** (`libs/<lib>`) checked out at that SHA
   and committed (`git submodule status` shows it). If the submodule tracks a
   slightly later commit for build/CI fixes only, say so in the README — but
   the spec pins the fit commit.
3. **A tag in the library repo** so the SHA has a name:
   ```bash
   git -C <lib-clone> tag -a <project>-paper <sha> -m "Commit used for the <project> paper fits"
   git -C <lib-clone> push origin <project>-paper
   ```
   If the library has Zenodo–GitHub integration, a GitHub *release* from this
   tag mints a DOI for exactly that version — cite it in Code Availability.
4. **The README** installation section.

Verify, every time an env is built or a MATLAB session starts:

```bash
python -c "import <lib>; print(<lib>.__file__, getattr(<lib>, '__version__', '?'))"
Rscript -e 'packageDescription("<lib>")[c("Version","RemoteSha")]'
matlab -batch "setup_paths; which -all <lib_entry_function>"     # exactly one hit, inside libs/
git -C libs/<lib> rev-parse HEAD                                  # must equal the pinned SHA
```

**Path pollution is the trap in every language.** A Python editable install
of one shared clone into many envs (`pip install -e`), a MATLAB `startup.m`
or saved `pathdef.m` that adds another copy of SPM/the toolbox, an R
`.libPaths()` with a user library ahead of `renv` — each silently repoints
the library for every analysis, and nothing raises. `which -all`,
`<lib>.__file__` and `.libPaths()` are the checks; run them before trusting
any result.

For development against the pinned version without touching a shared
checkout (Python/R), use a worktree:

```bash
git -C <lib-clone> worktree add "$(pwd)/src/<lib>" <sha>   # src/ is gitignored
pip install -e "$(pwd)/src/<lib>"                          # or devtools::load_all("src/<lib>")
```

### When the old library no longer runs on new dependencies

An old in-house library on a newer dependency typically breaks on one removed
keyword or renamed function (bauer 0.1.0 on PyMC ≥ 5.16: the `mutable=`
kwarg of `pm.Data` was removed). The fix is a **shim** that patches exactly
that and touches nothing in the likelihood/model — placed in the project (not
the library), called explicitly by every figure script, a no-op under the
original dependency version. Document it in the README: what it patches,
that fitted values are unchanged, and how you checked. Shimming is
acceptable; silently upgrading the library is not.

## Software outside the language environment

A table in the README; versions from artifacts, not memory:

| Software | Version | Where recorded | How it ran |
|---|---|---|---|
| fMRIPrep | 23.2.1 | container path in the preprocessing job script; `GeneratedBy` in derivatives | Apptainer/Singularity/Docker image |
| FreeSurfer | 7.3.2 | bundled in the fMRIPrep image (`recon-all -version` in `scripts/recon-all.log`) | via fMRIPrep |
| SPM | 12, r7771 | `spm('Ver')`; `SPM.SPMid` in `SPM.mat` | MATLAB R2023b |
| FSL / AFNI / ANTs | … | `fslversion`, `afni -ver`, `antsRegistration --version`; module names | cluster modules |
| MRIQC | 24.0.0 | container path | Apptainer |
| CmdStan / JAGS | … | project README | local |

Record the container image *digest* if you can (`apptainer inspect <img>`,
`docker inspect --format '{{.RepoDigests}}'`) — tags can be re-pushed,
digests cannot. The wrapper script that ran it is in the repo, so the exact
flags are recorded.

## Containers

A Dockerfile/Apptainer definition is a bonus, not a requirement, when the
stack is lockable (conda, renv). Worth it when the env depends on a system
library, a specific CUDA/driver combination, or a MATLAB release. If you
ship one, build it from the lock file, not the spec, and record the built
image's digest in the README.
