# ============================================================================
# REAL EXEMPLAR — excerpted from a working project.
#
# Provenance: ~/git/tms_risk/tms_risk/behavior/fit_model.py @ 846d8fd
#             (TMS × risk-attitudes; PMC family of bauer cognitive models)
#
# What to study (the bauer-model dispatch pattern):
#   * Module docstring is a LIVE MODEL TABLE — short labels → what each
#     model assumes. Re-grouped by family (Weber PMC, Flexible PMC, DDM ×
#     Flexible PMC, RDM × Flexible PMC, session-1 baselines). Legacy labels
#     are explicitly named and pushed into a sibling `legacy_models.py`.
#     Worth replicating: a model table that lives next to the dispatch.
#   * Single `build_model(model_label, df)` switch that calls per-family
#     builders (`_build_flexible`, `_build_ddm_or_rdm`). Each family parses
#     its own suffix grammar (`flexible1.4a`, `ddm_flexible_perception`...).
#   * `_stim(*names)` helper for the repetitive "regressor on
#     stimulation_condition" recipe — keeps the dispatch readable.
#   * Optional model classes are guarded with `try: from bauer.models import
#     ...; except ImportError: X = None`, then checked at use site —
#     accommodates older bauer installs that lack DDM/RDM extras.
#   * Sampler config is family-dependent: DDM/RDM jobs go on the numpyro
#     backend with shorter chains (1000+1000) per the bauer lesson 8
#     reference; everything else gets pymc + 5000+5000. target_accept
#     is bumped to 0.9 for the trickier likelihoods.
#   * `get_data()` does model-aware data prep: drops baseline trials for
#     non-session1 fits; gates trials at rt >= 0.20 s for DDM/RDM (WFPT
#     likelihood floors below t0; trapping NUTS). Document the *why*.
#
# EXCERPT NOTE: The Weber PMC family branches (1c, 10a–10c, 11a–11c, 12a–12e)
# and the legacy-model fallback have been condensed below to a representative
# few. See the provenance file for the full dispatch.
# ============================================================================
"""Fit bauer cognitive models by short string label.

Live model labels (referenced by analysis notebooks):

    Weber PMC family (RiskRegressionModel):
        1c                      n2_evidence_sd ~ stim (single noise regressor)
        10_null, 10a, 10b, 10c  TMS on n1/n2 evidence noise (independent memory)
        11_null, 11a, 11b, 11c  TMS on perceptual / memory noise (shared mem)
        12a, 12b, 12c, 12d, 12e TMS on prior μ / σ for risky / safe options

    Flexible PMC family (FlexibleNoiseRiskRegressionModel) — paper's main model:
        flexible1[.4|.6][_null|a|b]  TMS on n1/n2 evidence noise, polynomial orders 3/4/6
        flexible2[.4|.6][_null|a|b]  TMS on perceptual / memory noise, polynomial orders 3/4/6

        Suffix legend: '_null' = no TMS regressor; 'a' = only n1/memory;
        'b' = only n2/perceptual; bare label = both.

    DDM × Flexible PMC family (DDMFlexibleNoiseRiskRegressionModel) — Phase 5:
        ddm_flexible[_null|_perception|_memory|_threshold|_noise_threshold]

    Race-diffusion × Flexible PMC family (RaceDiffusionFlexibleNoiseRiskRegressionModel):
        rdm_flexible[_null|_perception|_memory|_threshold|_noise_threshold]

    Session-1 baselines (RiskModel, no TMS regressor):
        everyone                fit pooled across all sessions/subjects
        session1_full           prior_estimate='full', separate n1/n2 noise

Legacy labels (kept for reference in legacy_models.py): 1, 1_null, 1a, 1b,
1_session, 2*, 3*, 5*, 6*, 7, session1_*, 20, 21. They were exploratory
variants that no live notebook references — pruning them keeps this
dispatch readable. See legacy_models.py to resurrect one.
"""
import argparse
from pathlib import Path

import arviz as az
import numpy as np

from bauer.models import (
    RiskModel,
    RiskRegressionModel,
    FlexibleNoiseRiskRegressionModel,
)
try:
    from bauer.models import DDMFlexibleNoiseRiskRegressionModel
except ImportError:
    DDMFlexibleNoiseRiskRegressionModel = None
try:
    from bauer.models import RaceDiffusionFlexibleNoiseRiskRegressionModel
except ImportError:
    RaceDiffusionFlexibleNoiseRiskRegressionModel = None

from tms_risk.utils.data import get_all_behavior


def main(model_label, burnin=None, samples=None, bids_folder='/data/ds-tmsrisk',
         backend=None):

    df = get_data(bids_folder, model_label=model_label)

    target_folder = Path(bids_folder) / 'derivatives' / 'cogmodels'
    target_folder.mkdir(parents=True, exist_ok=True)

    is_accumulator = model_label.startswith('ddm_') or model_label.startswith('rdm_')

    if (model_label.startswith('flexible')
            or is_accumulator
            or model_label.startswith('session1')):
        target_accept = 0.9
    else:
        target_accept = 0.8

    # DDM/RDM fits are slow under pymc's NUTS — bauer's lesson 8 puts them
    # on the numpyro backend, which is 3–10× faster on CPU and parallelises
    # cleanly. Use shorter chains there (1000+1000 is what lesson 8 uses
    # and what passes diagnostics on the Garcia 2022 dataset).
    if is_accumulator:
        burnin = burnin or 1000
        samples = samples or 1000
        backend = backend or 'numpyro'
    else:
        burnin = burnin or 5000
        samples = samples or 5000
        backend = backend or 'pymc'

    model = build_model(model_label, df)
    model.build_estimation_model()
    trace = model.sample(burnin, samples, target_accept=target_accept,
                         backend=backend)
    az.to_netcdf(trace, str(target_folder / f'model-{model_label}_trace.netcdf'))


# ---------------------------------------------------------------------------
# Helpers for repeated regressor recipes
# ---------------------------------------------------------------------------

def _stim(*names):
    """Build {name: 'stimulation_condition', ...} regressor dict."""
    return {n: 'stimulation_condition' for n in names}


def _flexible_noise_regressors(suffix, memory_model):
    """Regressor dict for the flexible PMC family.

    suffix: '' (both noise terms), 'a' (n1/memory only), 'b' (n2/perceptual only),
            '_null' (no TMS effect on noise).
    memory_model: 'independent' (flexible1 family) → uses n1/n2_evidence_sd
                  'shared_perceptual_noise' (flexible2 family) → uses
                  memory_noise_sd / perceptual_noise_sd
    """
    if suffix == '_null':
        return {}
    if memory_model == 'independent':
        first, second = 'n1_evidence_sd', 'n2_evidence_sd'
    else:
        first, second = 'memory_noise_sd', 'perceptual_noise_sd'
    if suffix == 'a':
        return _stim(first)
    if suffix == 'b':
        return _stim(second)
    return _stim(first, second)


def _build_flexible(model_label, df):
    """Dispatch flexible1[.4|.6][_null|a|b] / flexible2[.4|.6][_null|a|b]."""
    rest = model_label[len('flexible'):]
    family_digit = rest[0]            # '1' or '2'
    rest = rest[1:]
    polynomial_order = 5
    if rest.startswith('.4'):
        polynomial_order = 4
        rest = rest[2:]
    elif rest.startswith('.6'):
        polynomial_order = 6
        rest = rest[2:]
    if rest == '_null':
        suffix = '_null'
    elif rest in ('a', 'b'):
        suffix = rest
    elif rest == '':
        suffix = ''
    else:
        raise Exception(f'Unrecognised flexible suffix: {rest!r}')

    memory_model = 'independent' if family_digit == '1' else 'shared_perceptual_noise'
    regressors = _flexible_noise_regressors(suffix, memory_model)
    return FlexibleNoiseRiskRegressionModel(
        df, regressors=regressors,
        polynomial_order=polynomial_order,
        memory_model=memory_model,
        prior_estimate='full',
    )


# ---------------------------------------------------------------------------
# Main dispatch
# ---------------------------------------------------------------------------

def build_model(model_label, df):

    # Flexible PMC family — paper's main model
    if model_label.startswith('flexible'):
        return _build_flexible(model_label, df)

    # DDM / RDM × Flexible PMC family — see provenance file for _build_ddm_or_rdm
    if model_label.startswith('ddm_') or model_label.startswith('rdm_'):
        from tms_risk.behavior.fit_model import _build_ddm_or_rdm  # not shown here
        return _build_ddm_or_rdm(model_label, df)

    # Weber PMC family (RiskRegressionModel) — representative branches only;
    # see provenance file for the full 10*/11*/12* dispatch.
    if model_label == '1c':
        return RiskRegressionModel(
            df, regressors={'n2_evidence_sd': 'stimulation_condition'},
            prior_estimate='full',
        )
    if model_label == '11a':
        return RiskRegressionModel(
            df, regressors=_stim('memory_noise_sd', 'perceptual_noise_sd'),
            memory_model='shared_perceptual_noise', prior_estimate='full',
        )

    # Session-1 baselines (no TMS regressor)
    if model_label == 'everyone':
        return RiskModel(df)
    if model_label == 'session1_full':
        return RiskModel(df, prior_estimate='full', fit_seperate_evidence_sd=True)

    # Legacy / dead labels — see legacy_models.py
    try:
        from tms_risk.behavior.legacy_models import build_legacy_model
    except ImportError:
        build_legacy_model = None
    if build_legacy_model is not None:
        legacy = build_legacy_model(model_label, df)
        if legacy is not None:
            return legacy

    raise Exception(f'Do not know model label {model_label}')


def get_data(bids_folder='/data/ds-tmsrisk', model_label=None):

    if model_label is not None and model_label.endswith('everyone'):
        df = get_all_behavior(bids_folder=bids_folder, all_tms_conditions=False, exclude_outliers=True)
        df = df.xs(1, 0, 'session', drop_level=False)
    elif model_label is not None and model_label.startswith('session1'):
        df = get_all_behavior(bids_folder=bids_folder, all_tms_conditions=True, exclude_outliers=True)
        df = df.xs(1, 0, 'session', drop_level=False)
    else:
        df = get_all_behavior(bids_folder=bids_folder, all_tms_conditions=True, exclude_outliers=True)
        df = df.drop('baseline', level='stimulation_condition')

    df = df.reset_index('stimulation_condition')
    df = df.reset_index('session')
    df['choice'] = df['choice'] == 2.0

    # DDM/RDM likelihoods (WFPT) require t0 < min(rt) per subject. Trials with
    # implausibly short RTs let the sampler wander into the t0 > rt region where
    # the WFPT log-likelihood floors at -66.1 and the gradient w.r.t. t0 is
    # exactly zero, which can trap NUTS at a wrong posterior. Mirror the
    # 0.20 s cutoff used in the bauer lesson 8 tutorial.
    if model_label is not None and (model_label.startswith('ddm_')
                                     or model_label.startswith('rdm_')):
        before = len(df)
        df = df[df['rt'] >= 0.20].copy()
        dropped = before - len(df)
        if dropped:
            print(f'Dropped {dropped} / {before} trials with rt < 0.20s '
                  f'({100 * dropped / before:.1f}%) for DDM/RDM fit.')

    return df


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('model_label', default=None)
    parser.add_argument('--bids_folder', default='/data/ds-tmsrisk')
    args = parser.parse_args()
    main(args.model_label, bids_folder=args.bids_folder)
