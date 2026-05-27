# Optional Subject-class patterns

These apply when the paradigm calls for them. Adopt when relevant;
skip when not.

## Derivative-name composition from boolean flags

retinonumeral does `encoding_model.cv.smoothed/`. If you adopt this,
define `_DERIV_FLAG_ORDER = (...)` as a module constant; both the
writer and reader compose names through the same helper. If your flags
are simple (one or two booleans), separate methods are cleaner — don't
build a composition machinery for two cases.

## Module-level experimental constants

retsupp's `distractor_locations` / `location_angles` are imported by
downstream code rather than redefined. Worth doing whenever you have
geometric constants used across modules. Keep them next to (or inside)
the Subject class file so they live in the same single-source-of-truth
module.

## A "master DataFrame" entry point

retsupp's `get_conditionwise_summary_prf_pars(model=8)` returns a
long-format DataFrame with PRF params × ROI labels × condition
pre-joined. Worth replicating if your paradigm has conditions and you
find downstream code doing the same join repeatedly. The cost is one
more cached intermediate to keep fresh; the benefit is that plotting /
stats code stays trivially short.
