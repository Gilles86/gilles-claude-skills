---
name: bayesian-workflow
description: Fitting and checking hierarchical Bayesian and cognitive models with PyMC / NumPyro / arviz / bauer / HSSM — convergence triage (divergences, r_hat, ESS, max-treedepth saturation), identifiability and parameter recovery, posterior predictive checks that can actually fail, model comparison with LOO/WAIC, and the sampler/grid traps that silently corrupt a fit. Use whenever fitting or debugging a Bayesian or cognitive model, when a fit will not converge or is mysteriously slow, when a parameter runs away or two parameters trade off, when deciding whether a result is trustworthy enough to report, when comparing models, or when building a posterior predictive check. Triggers on pymc, numpyro, arviz, bauer, HSSM, "divergences", "r_hat", "the chains", "the trace", "posterior", "MCMC", "model comparison", "LOO". Pairs with the **scientific-figures** skill, which covers how to DRAW the resulting posteriors and PPCs.
---

# Bayesian model fitting and checking

The failure mode this skill exists to prevent: reading parameters off a fit
that never earned the right to be interpreted. A hierarchical model will
happily return a tidy per-subject parameter table when the sampler diverged
5000 times, when the parameter is unidentified and the posterior is just the
prior, or when the discretization grid cannot resolve the value being
estimated. None of those announce themselves in the output table.

## The order of operations

Each gate is a precondition for the next. Do not skip forward because the
numbers "look reasonable" — reasonable-looking numbers are exactly what a
degenerate fit produces.

1. **Does the design identify the parameters?** Before fitting, name what in
   the data distinguishes each parameter from the others. No sampler fixes a
   design with no leverage.
2. **Did the sampler converge?** r_hat, ESS, divergences, tree depth.
3. **Can the model recover its own parameters?** Simulate from known values,
   refit, check the diagonal. Do this before believing any newly added
   parameter.
4. **Does the model reproduce the data?** Posterior predictive checks that
   are capable of failing.
5. **Only then**: compare models, correlate parameters with other measures,
   put numbers in a paper.

## Convergence triage

Read the symptom, not the summary line. `az.summary` reporting `r_hat < 1.01`
does **not** mean the fit is fine; it means the chains agree, which they can
do while all being stuck in the same bad place.

| Symptom | What it usually means | What to do |
| --- | --- | --- |
| `r_hat > 1.01` on any parameter | Chains disagree — not converged, full stop | Longer tuning, better parameterization; never just report it |
| Low `ess_bulk` / `ess_tail` (< ~400) | Heavy autocorrelation; posterior summaries are noisy | More draws, reparameterize; check for a funnel |
| A handful of divergences (< ~1% of draws) | Usually curvature the step size missed | Raise `target_accept` to 0.95–0.99 |
| Many divergences (> ~5% of draws) | Geometry is wrong, not the tuning | Reparameterize (non-centered), bound or fix the offending parameter. `target_accept` will NOT save this |
| **Max tree depth saturated** (1023 = 2^10 − 1 leapfrog steps on a large fraction of iterations) | The posterior has a long thin ridge — typically two parameters trading off, i.e. weak identifiability | Fix the model, not the sampler. Count it: `grep -c "1023 steps"` against total iterations |
| Wall clock 10–50× expected | Almost always the tree-depth problem above, not model size | Same fix. A 2-parameter model taking 18 h/chain is a geometry diagnosis, not a compute problem |
| A parameter's posterior sits at the edge of its prior | The likelihood is flat there; the prior is doing the work | Check what the data can actually resolve (see grid ceilings below) |

Non-centered parameterization is the first thing to try for a hierarchical
funnel. Divergences concentrated at small group-SD values are the signature.

## Identifiability before interpretation

**Ask the design question in words first.** For each pair of parameters:
*what pattern in the data would look different if I moved parameter A but not
parameter B?* If the answer is "nothing much", the parameters are not
separable, and a clean-looking hierarchical fit is a false comfort — the
group-level prior and the hyperprior tails will invent a value.

Signatures of a non-identified pair, in ascending order of how obvious they are:

- Estimates of one parameter reproduce a simpler model's estimates almost
  exactly (correlate them: r > 0.95 across subjects is damning)
- One parameter runs to the edge of what the grid or prior allows
- Max tree depth saturates; wall clock explodes
- Divergences in the thousands

**Worked example** (abstract_values, 2026-08): a two-stage efficient-coding
model with perceptual noise `kappa_r` and value noise `sigma_rep`. Under a
*uniform* perceptual prior the first stage adds variance but no bias, so it
collapses onto the value-noise-only model: `sigma_rep` correlated r = 0.99
with the simpler model's estimates, `kappa_r` ran past the grid's resolution
ceiling, 5980 divergences, 100 parameters with r_hat > 1.01. Under the
*structured* (cardinal) prior the first stage produces a bias signature that
the second stage cannot mimic, and the same model is identified. The fix was
not sampling harder; it was recognising which prior made the design informative.

**The model-free leverage check.** Before or instead of fitting, test whether
the data show the signature the parameter is supposed to produce. If two
conditions imply different mappings from a latent variable to the response,
the noise attributable to the early stage must scale with the local slope of
that mapping and the late-stage noise must not — so correlate the
cross-condition ratio of response SD with the ratio of |slope|. A positive
correlation means the design has leverage; near zero means the fit cannot
separate the stages no matter how long it runs.

**Parameter recovery is not optional for a new parameter.** Simulate datasets
from known parameter values spanning the plausible range (same subjects, same
trial counts, same design), refit, and plot recovered against true. What you
are looking for is not just the diagonal but the *off*-diagonal: if recovered
`A` depends on true `B`, you have measured the trade-off directly.

**Grid and discretization ceilings.** Any model that evaluates a likelihood on
a grid can only resolve variability coarser than the grid spacing. Below that,
the likelihood is flat and the posterior is the prior. Compute the ceiling in
closed form and cap the prior at it rather than letting the sampler wander:
for an N-point grid over a circular variable, a von Mises concentration above
`(N / 2*pi)**2` is unresolvable. State the ceiling next to any estimate that
approaches it.

## Posterior predictive checks

The one thing to get right: **the band must come from SIMULATED DATA, not from
predicted means or probabilities.** A band built by aggregating the model's
predicted mean carries parameter uncertainty only; with a few thousand trials
that band is a hairline, ordinary sampling scatter reads as catastrophic
misfit, and people then paper over it by adding SEM error bars to the observed
points, which double-counts the noise and hides real misfit.

Compute the summary statistic **per posterior-predictive draw, then summarize
across draws** — never collapse draws first. Print the band's coverage every
time: for a nominal 95% band, roughly 95% of observed points should fall
inside. Far below means the band is too narrow (usually the bug above); far
above means the check has been smoothed until it cannot fail.

Full recipes — the two questions that catch most PPC bugs, the coverage test,
the mean-parameter trap, and the bauer / PyMC APIs that do and do not give you
simulated outcomes — are in
[references/ppc_construction.md](references/ppc_construction.md).

How to *draw* the resulting panel — visual hierarchy, no error bars on the
observed points, direct labels, caption language — belongs to the
**scientific-figures** skill
(`references/posterior_predictive_checks.md` there).

## Model comparison

- Compare only models that passed convergence and recovery. A model with 5000
  divergences has no defensible ELPD.
- LOO/WAIC via `arviz` needs pointwise log-likelihood. Models whose likelihood
  is attached with `pm.Potential` have no `observed_RVs`, so PyMC's JAX path
  **crashes in `_get_log_likelihood`** — after sampling, losing the whole fit.
  Do not pass `idata_kwargs={"log_likelihood": True}` to those models; compute
  the pointwise log-likelihood separately from the saved trace.
- Report the ELPD difference *and* its standard error. A difference smaller
  than ~2 SE is not a result.
- A model that wins on ELPD while failing the PPC has usually won on the bulk
  of easy trials. Say so.

## Priors

- Weakly informative by default; scale them to the units of the parameter, not
  to habit. `HalfCauchy` group SDs have tails long enough to let an
  unidentified subject-level parameter run away — that is often how a
  degenerate fit hides.
- Prior predictive check before fitting: simulate from the prior and look at
  the implied data. If the prior predicts responses that could never occur,
  the prior is wrong regardless of how "uninformative" it looks.
- Cap a prior at the resolution the data can support (see grid ceilings).

## Reporting

State, every time: sampler and version, chains/draws/tuning, `target_accept`,
divergence count, worst r_hat, minimum ESS, and what the PPC showed. If a
parameter is at a resolution ceiling or trading off with another, say it in
the same sentence as the estimate.

## Anti-patterns

- Reading a per-subject parameter table from a fit with thousands of divergences
- "`r_hat` is fine" as the whole convergence claim
- Raising `target_accept` to silence a geometry problem
- Adding a parameter without a recovery check
- A PPC band built from predicted means or probabilities
- Error bars on the observed points of a PPC
- Comparing models by ELPD without the SE of the difference
- Interpreting a parameter pinned at the edge of its prior as an estimate

## Operational traps

Sampler-, backend- and library-specific gotchas that cost real days — NumPyro
chain methods that silently serialize, JAX static-shape failures, memory
scaling, and bauer specifics — are in
[references/sampler_traps.md](references/sampler_traps.md).
