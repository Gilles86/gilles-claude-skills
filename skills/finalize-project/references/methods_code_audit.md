# Code ↔ Methods audit

Two passes, opposite directions. The forward pass catches Methods that
overstate or misstate what ran; the reverse pass catches decisions the code
made that the paper never mentions. Both are table-driven so nothing is
audited "by feel".

## Forward: Methods → code

### 1. Build the claims table

Paste the Methods (plus figure legends and SI methods) into a private note
(`notes/methods_audit.md`; `notes/` is gitignored because it quotes the
manuscript). One row per claim:

| id | section | claim (verbatim) | paper value | code location | invoked value | status | resolution |
|---|---|---|---|---|---|---|---|
| M07 | Preprocessing | "four dummy scans were discarded" | 4 | `cluster_preproc/fmriprep.sh:41` | `--dummy-scans 4` | match | — |
| M12 | nPRF | "up to 5000 gradient-descent iterations" | 5000 | `modeling/fit_model.py:212` | `max_n_iterations=5000` default, but `slurm_jobs/fit_model.sh` passes `--n_iter 3000` | **mismatch** | Methods → 3000; check date of the .sh change vs fit date |
| M15 | GLM | "smoothed with an 8 mm FWHM kernel" | 8 | `glm/batch_smooth.m:14` | `matlabbatch{1}.spm.spatial.smooth.fwhm = [6 6 6]`; `SPM.mat` of the fits confirms 6 | **mismatch** | Methods → 6 mm |

What counts as a claim — anything with a number, a name, or a choice:

- **Sample**: N recruited, N analysed, each exclusion and its reason, sessions/runs/trials per subject.
- **Acquisition**: field strength, sequence, TR, TE, voxel size, slices, dummy scans, fieldmaps, run length.
- **Preprocessing**: tool + version, output spaces, susceptibility correction, slice timing, smoothing FWHM (and *where* it is applied — fMRIPrep does not smooth), confound set, high-pass.
- **GLM / single-trial**: HRF model or library, regressor definition, denoising, ridge, which events.
- **ROI**: atlas/label source, threshold, hemisphere, how projected to native space.
- **Model**: functional form, parameter bounds, grid ranges, fixed constants (a `1.29` in a Methods sentence must be a `1.29` in the code), optimizer, learning rate, iterations, priors, hierarchical structure, sampler settings (chains, draws, warmup, `target_accept`).
- **Cross-validation**: number of folds, how folds are formed (by run? session? pairing rule?), what is refit per fold.
- **Selection thresholds**: cvR² > 0, R² > x, cluster-forming thresholds, RT cutoffs, no-response handling.
- **Decoding**: noise model family, covariance structure, regularization, grid over stimulus space.
- **Statistics**: test, one/two-sided, correction, CI type, n for each test, Bayesian vs frequentist p.
- **Software versions** and **seeds**.

### 2. Trace each claim to the *invoked* value

The value that matters is the one the production run used, not the first
constant you grep. Follow the chain end to end:

```
job script (.sh/.sbatch)  →  command-line flags  →  script defaults (argparse / inputParser / optparse)
                          →  function defaults  →  constants (incl. matlabbatch structs, config files)
```

- A job-script flag overrides a script default overrides a function default.
  Record the whole chain when they disagree.
- Notebooks and live scripts can override constants after loading. Search
  them too (`grep -n 'n_iter\|fwhm\|threshold' *.ipynb *.Rmd` — `.ipynb` is
  JSON; `.mlx` is a zip: `unzip -p fig.mlx matlab/document.xml | grep …`).
- The same constant often lives in several places (script, data loader,
  plotting code). List all; they must agree.
- The data-loading layer (a `Subject` class, `load_subject.m`, an R loader)
  hides decisions: default smoothing flags, default confound set, silent run
  exclusions in a subject table. Read it once, fully.

### 3. Trust artifacts over code

Code can be edited after the fits; artifacts cannot. When code and paper
disagree, ask the artifacts what ran:

| Artifact | What it tells you |
|---|---|
| Output directory names (`model31.smoothed.fit_responses/`) | flags that composed the derivative name |
| Sidecar JSONs, `dataset_description.json` `GeneratedBy` | tool + version for fMRIPrep-style derivatives |
| Job logs | echoed config, versions printed at startup, iteration counts |
| `SPM.mat` (`SPM.SPMid`, `SPM.xX`, `SPM.xBF`, `SPM.xVi`) | SPM revision and every design choice actually estimated |
| Fit metadata (MCMC trace attributes, fit manifests; some libraries stamp their commit) | library commit, sampler settings |
| Lock files, `conda env export` / `renv.lock` / `ver` output from the env that ran | package versions |
| `git log -- <script>` around the fit date | whether a constant changed *after* the fits |
| File mtimes of the derivatives vs commit dates | same, cross-check |

If the artifacts say one thing and the current code another, the paper follows
the artifacts, and the code either gets reverted to match or the affected fits
get redone with the current code. Document which, in the README's
"Reproducibility notes".

### 4. Triage mismatches

| Status | Meaning | Action |
|---|---|---|
| match | paper = invoked value | nothing |
| mismatch: paper wrong | code/artifacts agree, paper differs | Methods edit; list it for the response letter |
| mismatch: code drifted | current code ≠ what produced the artifacts | revert, or refit and regenerate figures, then re-audit |
| ambiguous | paper sentence admits two readings | rewrite the sentence; add the number |
| not in code | paper describes a step no code performs | find it (a notebook? a manual step?) or remove the claim |

Software versions: fill them from the lock file / container tag / `GeneratedBy`,
never from memory. `fmriprep --version` output in a log beats the README.

## Reverse: code → Methods

Walk every entry point the README names (pipeline stages + figure scripts +
stats script) and the data-loading layer. For each, list every **result-changing
decision**: a flag, a branch on subject/session, a threshold, a constant, a
default, a seed, an exclusion. Then check the paper for each.

Checklist of the usual omissions:

- Run/trial/subject exclusions applied in code (a subject table, RT cutoffs,
  NaN responses dropped, "first trial of each run dropped").
- Dummy scans / non-steady-state handling; whether onsets were shifted for them.
- Smoothing kernel and at which stage; whether analyses used smoothed or
  unsmoothed data (and whether *different* analyses used different ones).
- Confound regressors and high-pass/detrending.
- HRF choice and basis set; single-trial / denoising options (GLMsingle
  settings, SPM `matlabbatch` fields, LSS vs LSA, FIR length).
- CV fold construction rule (e.g. `run2 = (run-1) % 4 + 1` pairing) and what is
  held out.
- Voxel-selection threshold and whether it is computed in-fold or on all data.
- Grid-search ranges and bounds; softplus/log transforms of parameters;
  optimizer, learning rate, iteration count, early stopping.
- Noise model (Gaussian vs Student-t, dof fitted or fixed), covariance
  (spherical vs full), regularization λ.
- Priors, hierarchical structure, sampler and its settings, number of chains.
- Seeds (or the absence of seeding).
- Which fit variant feeds which figure (ground-truth vs response fits;
  smoothed vs unsmoothed; hemisphere).
- Software versions, including the in-house library commit.
- Anything done by hand: manual panel assembly, manually edited masks, hand-set
  colour ranges that imply a threshold.

**Output:** a list of Methods/SI additions with the code location for each.
Sanitized code-side facts ("all parameter analyses are restricted to voxels
with 8-fold cvR² > 0") also belong in the README's Reproducibility notes.

## Working practice

- One pass per Methods subsection; don't interleave. Finish the table before
  fixing anything — fixes change line numbers and tempt you to skip rows.
- If delegating a subsection to a subagent, hand it the manuscript text and the
  repo, not your conclusions; ask for `file:line` for every row.
- Keep the table until the paper is out. Reviewers and proofs will ask for a
  number you already traced.
