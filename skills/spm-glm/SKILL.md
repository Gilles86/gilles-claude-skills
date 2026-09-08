---
name: spm-glm
description: Running and auditing SPM12 GLMs driven by nipype — the parametric-modulator orthogonalisation trap (SPM orthogonalises serially by default and nipype silently drops `Bunch.orth`), how to verify what the design matrix actually did from SPM.mat, SnPM permutation second levels and cheap threshold sweeps, comparing contrast images correctly, and realistic SLURM sizing for first/second levels. Use whenever writing, submitting, or debugging an SPM first- or second-level analysis, a nipype `Level1Design` / `EstimateModel` / SnPM workflow, when a Methods section claims something about orthogonalisation, when a parametric modulator's map looks suspiciously like another regressor's map with the sign flipped, or when deciding SLURM resources for MATLAB/SPM jobs.
---

# SPM GLMs through nipype

Operational knowledge for mass-univariate SPM12 analyses driven by nipype
(`Level1Design` → `EstimateModel` → `EstimateContrast`, SnPM for the second
level). Pairs with the **sciencecluster** skill (SLURM specifics) and
**cogneuro-project** (where these scripts live in the repo layout).

The single most important habit: **verify what SPM did from `SPM.mat`, never
from the code's intent or the paper's Methods section.**

## Serial orthogonalisation of parametric modulators

SPM orthogonalises the parametric modulators of a condition *serially, against
each other and against the condition's main regressor*, unless told otherwise.
The flag lives at `SPM.Sess(k).U(j).orth` and **defaults to 1**.

### Nipype silently drops your intent

`SpecifySPMModel`'s `Bunch` accepts an `orth` field. Nothing reads it: there is
no handling of `Bunch.orth` in `nipype/algorithms/modelgen.py` (its only `orth`
is an internal helper for temporal derivatives) or anywhere in
`nipype/interfaces/spm/`. Passing `orth=["No"] * len(conditions)` is a no-op, so
the design is orthogonalised and a Methods sentence saying otherwise is wrong.

Check it, in five lines:

```python
import scipy.io as sio, numpy as np
spm = sio.loadmat(spm_mat, struct_as_record=False, squeeze_me=True)["SPM"]
for u in np.atleast_1d(np.atleast_1d(spm.Sess)[0].U):
    print(u.name, u.orth)          # orth == 1 -> SPM orthogonalised this condition
```

Second fingerprint, from the design matrix itself: **the correlation between two
modulator columns of the same condition is exactly 0.0000** when `spm_orth` has
run. A real task rarely produces exactly zero.

### The algebra, and the direction everyone gets backwards

Serial orthogonalisation is a reparameterisation, not a change of model span:
`X_orth = X_raw · T` with `T` unit upper-triangular, so

    beta_raw = T · beta_orth
    beta_orth[m1] = beta_raw[m1] + a · beta_raw[m2],   a = cov(m1, m2) / var(m1)

Consequences, for modulators entered in the order `m1, m2`:

- **The LAST modulator is estimated identically either way.** Its contrast
  images are bit-identical to float32 rounding (~1e-8 relative).
- **Earlier modulators absorb the shared variance.** `m1`'s map is the one that
  moves — it carries `a ×` the *other* modulator's effect.

The natural but wrong inference is the opposite one: because the *column* that
visibly changes is `m2` (it is the one `spm_orth` residualises), it is tempting
to conclude the `m2` map is the contaminated one. Comparing design-matrix
columns answers the wrong question. **Compare the parameter estimates.**

So with `m2` carrying a big effect and `a < 0`, orthogonalisation manufactures a
widespread *negative* `m1` map that is just `−|a| ×` the `m2` map. A worked
case (multlearn, unsigned then signed RPE at feedback, mean `a = −0.25`): the
negative uRPE map collapsed from 10,293 to 1,160 voxels at p < .001 once orth
was off, and the change in the uRPE t map correlated −0.86 with the signed-RPE
t map. Diagnostics worth running whenever two modulators share an event:

```python
# does the map that moved move *like* the other regressor's map?
np.corrcoef(t_orth - t_noorth, t_other_regressor)   # ~ -0.9 = artefact signature
```

### Actually turning it off

SPM12's batch exposes `spm.stats.fmri_spec.sess.cond.orth`; nipype never writes
it. Two routes, both fine:

1. A MATLAB step between `Level1Design` and `EstimateModel` that loads
   `SPM.mat`, sets `SPM.Sess(k).U(j).orth = 0` everywhere and calls
   `spm_fMRI_design(SPM)` to rebuild `SPM.xX.X`. Smallest change to an existing
   nipype pipeline.
2. Emit the `matlabbatch` for the design directly, bypassing the Bunch.

Write the refit to a **parallel output tree** (`nipype/model7_noorth/`), never
in place: the original results stay reproducible, and everything downstream
that is parameterised by model name drops straight in.

## Comparing contrast images: data, not checksums

SPM stamps provenance (paths, `descrip`, timestamps) into the NIfTI header, so
`md5sum` differs between two runs even when every voxel is identical. Always
compare the arrays:

```python
A, B = [np.asarray(nib.load(f).dataobj, np.float64) for f in (fa, fb)]
rel = np.abs(A - B).max() / np.abs(A).max()      # ~1e-8 = identical, float32 noise
```

Also relevant here: writing derived maps back through a binary mask inherits the
mask's `uint8` dtype and quantises everything — always
`img.set_data_dtype(np.float32); img.header.set_slope_inter(1, 0)`.

## SnPM second levels

- `ST_later` (`ST_U = -1`) stores the suprathreshold "mountain tops" for every
  permutation down to `ST_Ut = t(p = .01, df)`. **Any cluster-forming threshold
  at or above that can be re-inferred by re-running `snpm_pp` only** — a whole
  threshold sweep costs seconds, not another 5000 permutations. Check
  `SnPM_ST.mat` exists before planning a re-permutation.
- `snpm_pp` always loops over both tails and dies on an undefined `Locs_vox`
  when a tail has no suprathreshold voxels. That is an empty result, not a
  failure; catch the message and record "empty".
- Re-running inference writes new `SnPM_filtered_*` files plus the regenerable
  `SnPM_pp.mat` / `SnPM_pp_Neg.mat`. `SnPM.mat`, `SnPM_ST.mat` and `STCS.mat`
  are only read — so a sweep does not endanger the published maps, as long as
  the new filtered images use distinct names.
- Cross-checking with `nilearn.glm.second_level.non_parametric_inference` is
  cheap and buys TFCE and a two-tailed family, but note two engine differences:
  nilearn labels clusters with 6-connectivity (SPM uses 18), and its `threshold`
  argument is a **p-value**, halved internally when `two_sided_test=True`.

## SLURM sizing: measure, then stop over-requesting

Measured on 58 subjects × 6 runs, ~60k-voxel ICV mask, SPM12 + MATLAB r2023b:

| Job | Actual | Ask for |
| --- | --- | --- |
| First level, one subject, nipype MultiProc, 16 cores | **3.5 min** | 30 min |
| SnPM second level: the 5000 permutations themselves | **~3 min** | — |
| SnPM `snpm_pp` cluster inference, per (threshold, sign) | **2–4 min** | — |
| ...so a second level plus inference at 3 thresholds, both tails | ~20–30 min | 1 h |
| `non_parametric_inference`, 5000 perms, one cluster threshold | ~5 min | — |
| `non_parametric_inference`, 5000 perms, TFCE | ~70 min | 3 h |

Note the split in the SnPM row: the permutation stage is fast, and `snpm_pp` is where the
time goes, because it walks the 5000 permutations again to build the max-cluster-size
distribution — once per cluster-forming threshold *and* per tail. A five-threshold,
two-tailed sweep is therefore ~30–50 min per analysis, not the ~3 min the `SnPM.mat`
timestamp suggests.

A 20-hour `--time` on a four-minute job is not free insurance: SLURM's backfill
scheduler can only slot a job into a gap it declares it will fit in, so an
over-long limit means waiting behind everything while a 30-minute request drops
into the next hole. Get the real number once —

```bash
sacct -u $USER --starttime now-2days -X --name=<jobname> \
      --format=JobName%20,Elapsed,MaxRSS,ReqMem,AllocCPUS
```

— then set the limit to roughly 10× it and move on. For an old analysis with no
job records, the file mtimes inside the output directory bracket the run
(`SnPMcfg.mat` → `SnPM.mat` is the permutation loop).

## `module` is a shell function, and sbatch does not inherit it

`sbatch` exports the *submitting* environment. Submitted from a login shell,
`module` exists; submitted non-interactively (`ssh host 'sbatch job.sh'`, a
cron, an agent), it does not — and the failure is silent and confusing:

```
/var/spool/slurmd/jobNNN/slurm_script: line 20: module: command not found
GLM_2ndlevel.py: error: argument --mlab_path: expected one argument
```

because `--mlab_path $(command -v matlab)` expanded to nothing. Make every job
script self-sufficient rather than relying on how it was submitted:

```bash
# `module` is a function defined by lmod.sh, and MODULEPATH is set by
# z01_lmodenv.sh -- sourcing only the first gives a `module` that then reports
# the module does not exist, which is a very confusing way to fail
for f in /etc/profile.d/lmod.sh /etc/profile.d/z01_lmodenv.sh \
         /etc/profile.d/lmod_ignore_cache.sh; do
    [ -r "$f" ] && source "$f"
done
module load matlab/r2023b          # also puts apptainer on PATH for the wrapper
MATLAB=$(command -v matlab)
test -n "$MATLAB" || { echo "matlab not on PATH after module load"; exit 1; }
```

`source /etc/profile` does **not** substitute for those two lines (tested: it
leaves `MODULEPATH` unset in a non-login `bash -c`). Both failures look
different and neither says "you submitted this from the wrong kind of shell":

```
line 20: module: command not found          # lmod.sh not sourced
Unable to locate a modulefile for 'matlab/r2023b'   # MODULEPATH not set
```

Never hardcode the MATLAB path — it moves with OS upgrades (on sciencecluster it
became `/apps/u24/opt/containers/bin/matlab/r2023b/matlab`, breaking scripts
that had `/apps/opt/...` baked in).

Also: nipype writes node working directories into the **current** directory, so
`cd` somewhere deliberate in the job script or they land in `$HOME`.

## Audit checklist for an inherited SPM analysis

1. `SPM.Sess(k).U(j).orth` for every condition — and the modulator correlations
   in `SPM.xX.X`, which say whether `spm_orth` ran.
2. Modulator *order* within each condition: the first one keeps shared variance.
3. Contrast weights (`SPM.xCon(i).c`) against what the paper says they are.
4. `SPM.xX.K` / high-pass, `SPM.xVi` (AR(1) vs none), and the analysis mask —
   an implicit mask silently shrinks the second level's voxel count.
5. Whether the second level's subject list matches the first level's; exclusions
   drift between analysis stages more often than anyone expects.
