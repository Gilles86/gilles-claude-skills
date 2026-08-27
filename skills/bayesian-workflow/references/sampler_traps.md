# Sampler, backend and library traps

**When to load:** a fit is mysteriously slow, dies after sampling, silently
ignores a setting, or blows past memory. These are the ones that cost days
rather than minutes, all confirmed against real runs.

## NumPyro

### `chain_method="parallel"` silently serialises on CPU

NumPyro's `parallel` chain method `pmap`s over JAX **devices**. On CPU there is
exactly one device unless XLA is told otherwise, so `parallel` quietly runs one
chain at a time — with no warning that survives into a SLURM log.

```bash
export XLA_FLAGS="--xla_force_host_platform_device_count=$CHAINS"
```

Verify from the log rather than trusting the flag: genuinely parallel chains
print interleaved `Running chain 0:` … `Running chain 3:` progress lines.
Sequential chains print one chain's bar to completion before the next starts.

Measured impact on one 26-subject grid model: 18.5 h per chain. Serialised,
four chains needed 74 h and died at a 24 h wall limit having produced nothing;
parallel, the same fit ran all four chains in ~22 h wall clock.

### `parallel` / `vectorized` multiply peak memory

Sequential chains held ~4 GB. The same model with parallel chains OOM'd at
64 GB and again at 192 GB. Budget per-chain peak × chains, plus XLA's
compilation buffers, and measure with `sacct -j <id> --format=MaxRSS` rather
than guessing. On GPU, `vectorized` batches chains into one program — check
device memory, not host memory.

### Wall-clock planning

Ask for the wall clock the *chain* needs, not the wall clock that feels
polite. A job killed at 95% produces nothing at all; SLURM partitions with
`MaxTime=UNLIMITED` make a 3-day request free. Check with
`scontrol show partition | grep MaxTime` before assuming 24 h is the cap.

## PyMC

### `pm.Potential` likelihoods break `log_likelihood`

A model whose likelihood is attached with `pm.Potential` has an empty
`observed_RVs`. PyMC's JAX sampling path then dies inside
`_get_log_likelihood` with `'NoneType' object is not iterable` — **after
sampling completes**, so the entire fit is lost. Never request
`idata_kwargs={"log_likelihood": True}` for such a model; compute the
pointwise log-likelihood separately from the saved trace when you need LOO.

## JAX static shapes

The JIT needs shapes to be concrete. Two patterns break it, both of which work
fine in the pytensor/C backend, so they surface only when someone switches to
NumPyro:

- **`pt.arange` over a symbolic length** (e.g. `pt.arange(x.shape[0])` where
  the length is a trial count) → *"requires the arguments of jax.numpy.arange
  to be constants"*. Replace the gather with a one-hot contraction over an axis
  whose length is a Python `int`:
  ```python
  cand = pt.arange(n_static)                      # length known at build time
  picked = pt.sum(values * pt.eq(cand[None, :], idx[:, None]), axis=1)
  ```
- **A tensor built from a fitted parameter losing its static shape** →
  *"Shapes must be 1D sequences of concrete values of integer type, got
  (JitTracer(int64[]), 51)"*. Every downstream reshape then carries a symbolic
  dimension. Pin it where the shape is lost:
  ```python
  ori_prior = pt.specify_shape(ori_prior, (n_subjects, n_grid))
  ```
  and pass grid lengths into helpers as Python ints rather than reading
  `x.shape[-1]`. This one appears *only* in hierarchical fits — a
  single-subject smoke test passes and hides it, so always smoke-test
  hierarchically.

**Smoke-test protocol before any cluster submission** of a changed model:
2 subjects, `draws=3, tune=3, chains=1`, `hierarchical=True`, the real
sampler backend. Thirty seconds locally, versus a day of queue plus a crash.

## Grid-likelihood models

- **Resolution ceiling.** A grid can only resolve variability coarser than its
  spacing; below that the likelihood is flat and the posterior is the prior.
  Compute the ceiling and cap the prior at it. For an N-point grid over a
  circular variable, von Mises concentrations above `(N / 2*pi)**2` are
  unresolvable (N=51 → 66; N=101 → 258).
- **Grid argmin makes the likelihood a step function.** Any estimator defined
  as an argmin over a grid moves in jumps as parameters change, so the
  gradient is zero almost everywhere and NUTS collapses the step size and
  saturates tree depth. Refine the argmin to sub-grid resolution (parabolic
  vertex through the three points around the minimum); the surface becomes
  smooth and the estimator gains accuracy for free.
- **Watch the intermediate rank.** Broadcast-and-sum over four indices
  materialises an O(N^3)–O(N^4) intermediate that must stay live for the
  backward pass. `pt.matmul` / `pt.dot` over reshaped axes computes the same
  thing without it — verify bit-comparability once (max abs diff ~1e-16), then
  keep the matmul.

## Hierarchical structure

- `subjectwise` vs trialwise expansion: grid models that build a
  `(n_subjects, ..., n_response)` table and gather it with `subject_ix` must be
  handed the **subject-level** `(n_subjects,)` RV. Feeding them the trialwise
  vector makes the leading axis `n_trials`, so `table[subject_ix]` reads the
  first `n_subjects` *trials* — all of which belong to subject 0. Every subject
  then shares subject 0's parameters and the group SD gets exactly zero
  gradient. Single-subject fits are unaffected, so this hides in testing.
- A `HalfCauchy` group SD has tails long enough to let an unidentified
  subject-level parameter run away to the edge of the grid. If a subject's
  estimate is implausible, check identifiability before blaming the subject.
