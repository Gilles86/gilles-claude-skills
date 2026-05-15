"""Bauer behavioral-model fit example (PyMC NUTS).

Hierarchical Bayesian model for risky choice. Adapt to project's
behavior/fit_riskmodel.py.

Run:
    python <package>/behavior/fit_riskmodel.py 1 --model RiskModel
"""
from __future__ import annotations

import argparse
from pathlib import Path


MODEL_CLASSES = {
    'RiskModel': 'RiskModel',                            # standard EU
    'RiskLapseModel': 'RiskLapseModel',                  # + lapse rate
    'LossAversionModel': 'LossAversionModel',            # gain/loss split
    'MagnitudeComparisonModel': 'MagnitudeComparisonModel',
    'MagnitudeComparisonLapseModel': 'MagnitudeComparisonLapseModel',
    'FlexibleNoiseRiskModel': 'FlexibleNoiseRiskModel',  # magnitude-dependent noise
    'RiskModelProbabilityDistortion': 'RiskModelProbabilityDistortion',
    'PsychometricModel': 'PsychometricModel',
}


def main(
    subject: int | None,
    bids_folder: str = '/data/ds-<project>',
    model_class: str = 'RiskModel',
    draws: int = 1000,
    tune: int = 1000,
    chains: int = 4,
    target_accept: float = 0.95,
    group: bool = False,
) -> None:
    print(f'[fit_cogmodel] subject={subject} model={model_class} '
          f'group={group} draws={draws} bids={bids_folder}', flush=True)

    # Heavy imports inside main()
    import bauer.models as bm
    from bauer.utils.bayes import get_posterior, summarize_ppc

    from <package>.utils.data import Subject

    # --- 1. Format trial data ---
    if group:
        # Pool across subjects for hierarchical fit
        from <package>.behavior.io import get_all_behavioral_data
        df = get_all_behavioral_data(bids_folder=bids_folder)
    else:
        sub = Subject(subject, bids_folder=bids_folder)
        df = sub.get_behavioral_data()

    # df should be long-format with at least:
    #   subject, condition, choice (0/1), and the magnitudes/probabilities
    #   the model needs (e.g., m1, m2, p1, p2 for RiskModel).

    # --- 2. Build model ---
    Model = getattr(bm, model_class)
    model = Model(df, prior_estimate='objective')

    # --- 3. NUTS sampling ---
    trace = model.fit(
        draws=draws,
        tune=tune,
        chains=chains,
        target_accept=target_accept,
        # init='adapt_diag',   # uncomment if divergences with default init
    )

    # --- 4. Posterior + PPC summaries ---
    posterior = get_posterior(trace, model)        # tidy DataFrame
    ppc = summarize_ppc(model, trace)              # posterior predictive

    # --- 5. Save ---
    out_dir = Path(bids_folder) / 'derivatives' / 'cogmodels' / model_class
    out_dir.mkdir(parents=True, exist_ok=True)

    tag = 'group' if group else f'sub-{subject:02d}'
    trace.to_netcdf(out_dir / f'{tag}_trace.nc')
    posterior.to_csv(out_dir / f'{tag}_posterior.tsv', sep='\t', index=False)
    ppc.to_csv(out_dir / f'{tag}_ppc.tsv', sep='\t', index=False)

    # Quick convergence sanity check (full diagnostics in notebook)
    import arviz as az
    summary = az.summary(trace, var_names=['~mu_intercept'], hdi_prob=0.94)
    print(summary[['mean', 'sd', 'r_hat', 'ess_bulk']].head(20), flush=True)
    bad_rhat = (summary['r_hat'] > 1.01).sum()
    if bad_rhat:
        print(f'WARNING: {bad_rhat} parameters with r_hat > 1.01', flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('subject', type=int, nargs='?', default=None,
                   help='subject number; omit if --group')
    p.add_argument('--bids_folder', default='/data/ds-<project>')
    p.add_argument('--model', dest='model_class', default='RiskModel',
                   choices=list(MODEL_CLASSES))
    p.add_argument('--draws', type=int, default=1000)
    p.add_argument('--tune', type=int, default=1000)
    p.add_argument('--chains', type=int, default=4)
    p.add_argument('--target_accept', type=float, default=0.95)
    p.add_argument('--group', action='store_true',
                   help='hierarchical fit across all subjects')
    args = p.parse_args()

    if not args.group and args.subject is None:
        p.error('subject required unless --group')

    main(
        subject=args.subject,
        bids_folder=args.bids_folder,
        model_class=args.model_class,
        draws=args.draws,
        tune=args.tune,
        chains=args.chains,
        target_accept=args.target_accept,
        group=args.group,
    )
