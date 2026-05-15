"""Braincoder PRF fit + decode example.

Three-stage fit (grid → refine baseline/amplitude → gradient descent),
followed by noise-model fit and stimulus decoding. Adapt to project's
modeling/fit_prf.py.

Run:
    python <package>/modeling/fit_prf.py 1 --model 4
"""
from __future__ import annotations

import argparse
from pathlib import Path


def main(
    subject: int,
    bids_folder: str = '/data/ds-<project>',
    model: int = 4,
    smoothed: bool = False,
) -> None:
    print(f'[fit_prf] subject={subject} model={model} '
          f'smoothed={smoothed} bids={bids_folder}', flush=True)

    # Heavy imports inside main() — see SKILL.md
    import numpy as np
    import pandas as pd
    from braincoder.hrf import SPMHRFModel
    from braincoder.models import GaussianPRF2DWithHRF
    from braincoder.optimize import (
        ParameterFitter,
        ResidualFitter,
        StimulusFitter,
    )
    from braincoder.utils import get_rsq

    from <package>.utils.data import Subject

    sub = Subject(subject, bids_folder=bids_folder)

    # --- 1. Load data ---
    bold = sub.get_single_trial_estimates(session=1, smoothed=smoothed,
                                          roi='V1')   # (n_trials, n_voxels)
    stimulus = sub.get_stimulus_grid(session=1)        # (n_trials, R, R)
    grid_coords = sub.get_grid_coordinates()           # (R*R, 2) — x, y per pixel

    # --- 2. Build model ---
    hrf_model = SPMHRFModel(tr=1.6)
    prf_model = GaussianPRF2DWithHRF(
        grid_coordinates=grid_coords,
        paradigm=stimulus,
        hrf_model=hrf_model,
        data=bold,
    )

    # --- 3. Three-stage fit ---
    fitter = ParameterFitter(model=prf_model, data=bold, paradigm=stimulus)

    # Stage 1: coarse grid search over (mu_x, mu_y, sigma)
    mu_grid = np.linspace(-5, 5, 20)
    sigma_grid = np.geomspace(0.3, 4.0, 10)
    grid_pars = fitter.fit_grid(
        mu_x=mu_grid, mu_y=mu_grid, sigma=sigma_grid,
        baseline_bounds=[None, None],
        amplitude_bounds=[1e-4, None],
    )

    # Stage 2: closed-form refine of baseline + amplitude
    refined_pars = fitter.refine_baseline_and_amplitude(grid_pars)

    # Stage 3: full gradient descent
    pars = fitter.fit(
        init_pars=refined_pars,
        learning_rate=0.05,
        max_n_iterations=1000,
        min_n_iterations=100,
        r2_atol=1e-4,
    )

    # R² per voxel
    pred = prf_model.predict(parameters=pars, paradigm=stimulus)
    r2 = get_rsq(bold, pred)
    pars['r2'] = r2.numpy()

    # --- 4. Save parameters ---
    out_dir = (Path(bids_folder) / 'derivatives'
               / ('modeling.smoothed' if smoothed else 'modeling')
               / sub.sub / 'func')
    out_dir.mkdir(parents=True, exist_ok=True)

    # TSV (fast reload for plotting)
    pars.to_csv(out_dir / f'{sub.sub}_model-{model}_pars.tsv', sep='\t')

    # NIfTI (one volume per parameter) — use _write_volume to avoid uint8 trap
    masker = sub.get_volume_mask(roi='V1', return_masker=True)
    for col in pars.columns:
        sub._write_volume(
            pars[col].values, masker,
            out_dir / f'{sub.sub}_model-{model}_desc-{col}_pe.nii.gz',
        )

    # --- 5. Fit noise model + decode (optional, for Bayesian decoding) ---
    resid_fitter = ResidualFitter(model=prf_model, data=bold, parameters=pars)
    omega, dof = resid_fitter.fit(method='t', init_dof=15.0)

    # Decode test data: returns posterior PDF over stimulus space per trial
    test_bold = sub.get_single_trial_estimates(session=2, roi='V1')
    stim_fitter = StimulusFitter(
        data=test_bold, model=prf_model,
        omega=omega, dof=dof,
    )
    stim_range = np.linspace(0, 50, 100)
    posteriors = stim_fitter.fit(stimulus_range=stim_range)
    posteriors.to_csv(out_dir / f'{sub.sub}_model-{model}_posteriors.tsv', sep='\t')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('subject', type=int)
    p.add_argument('--bids_folder', default='/data/ds-<project>')
    p.add_argument('--model', type=int, default=4)
    p.add_argument('--smoothed', action='store_true')
    args = p.parse_args()
    main(args.subject, bids_folder=args.bids_folder,
         model=args.model, smoothed=args.smoothed)
