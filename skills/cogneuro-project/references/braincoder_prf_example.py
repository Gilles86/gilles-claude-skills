#!/usr/bin/env python3
# ============================================================================
# REAL EXEMPLAR — excerpted from a working project.
#
# Provenance: ~/git/abstract_values/abstract_values/encoding_models/fit_aprf.py
#             @ a71c630
#
# What to study (the braincoder fitting pattern):
#   * Docstring lays out all model variants up front (standard /
#     session-shift / gaussian / gauss-session-shift) — when you have
#     multiple variants, document them in one place rather than spreading
#     across scripts.
#   * The 3-stage braincoder fit:
#       fit_grid(...)                          # coarse correlation-cost search
#       refine_baseline_and_amplitude(...)     # closed-form refinement —
#                                              # NEVER skip this step
#       fit(init_pars=..., max_n_iterations)   # gradient descent (Adam)
#     Fitter is `ParameterFitter(model, data, paradigm)`.
#   * Data prep: NiftiMasker.transform(betas_img).astype(np.float32) →
#     pd.DataFrame for braincoder. float32 throughout.
#   * Output paths follow BIDS derivatives:
#       derivatives/encoding_models/<variant>/sub-<sub>/func/...
#     with `_smoothed` suffix on filenames (not derivative dir name) when
#     the input was smoothed.
#   * Output writes use a tiny `save_f32(img, path)` helper that explicitly
#     casts to float32 — guards against the NIfTI dtype trap. Equivalent
#     to Subject._write_volume() pattern.
#   * `--debug` shrinks the grid and downsamples voxels for a fast smoke run,
#     and SKIPS saving so debug output never overwrites a real fit.
#
# EXCERPT NOTE: The session-shift, gaussian, and gauss-session-shift branches
# (≈190 lines) follow the same pattern as the `standard` branch shown below.
# See the provenance file for the full source.
# ============================================================================
"""
Fit an abstract pRF (Gaussian) encoding model to single-trial GLMsingle betas
using the OBJECTIVE VALUE of each trial's gabor stimulus as the paradigm.

Model
-----
  standard (default):
    LogGaussianPRF with parameters [mu, sd, amplitude, baseline].
    Always fits jointly across all available sessions of a subject.

  session-shift:
    SessionShiftedLogGaussianPRF — mu shifts freely between sessions while
    sd, amplitude, baseline are shared.  Requires at least 2 sessions.
    Parameters: [mu_1, mu_2, sd, amplitude, baseline].

  gaussian:
    GaussianValuePRF — symmetric Gaussian (no rightward skew).
    Parameters: [mode, fwhm, amplitude, baseline].

  gauss-session-shift:
    SessionShiftedGaussianValuePRF — symmetric Gaussian with mode shifting
    between sessions.  Requires at least 2 sessions.
    Parameters: [mode_1, mode_2, fwhm, amplitude, baseline].

Fitting is non-linear: grid search (correlation cost) followed by
gradient descent (Adam) via braincoder.optimize.ParameterFitter.

Output
------
  All variants always use the joint (all-sessions) output path — no
  ``ses-*`` directory or entity.

  standard:
    derivatives/encoding_models/aprf/sub-<subject>/func/
      params: mu, sd, amplitude, baseline, r2, fwhm

Usage
-----
  python fit_aprf.py pil01
  python fit_aprf.py pil01 --mask /path/to/mask.nii.gz
  python fit_aprf.py pil01 --model session-shift
  python fit_aprf.py pil01 --model gaussian
  python fit_aprf.py pil01 --model gauss-session-shift --debug
"""

import argparse
from pathlib import Path

import nibabel as nib
import numpy as np
import pandas as pd
from nilearn.maskers import NiftiMasker

from braincoder.models import LogGaussianPRF
from braincoder.optimize import ParameterFitter
from braincoder.utils import get_rsq

from abstract_values.utils.data import Subject, BIDS_FOLDER


def save_f32(img, path):
    """Save a NIfTI image as float32, regardless of mask dtype."""
    nib.Nifti1Image(img.get_fdata().astype(np.float32),
                    img.affine).to_filename(str(path))


def get_value_paradigm(sub, sessions):
    """Return DataFrame with column 'x' = objective CHF value (float32).

    Row order matches the gabor betas from fit_glmsingle:
    session → run (sorted) → events sorted by onset, gabor only.
    """
    rows = []
    for session in sessions:
        runs = sub.get_runs(session)
        events = sub.get_events(session, runs)
        for run in runs:
            run_ev = events.loc[run].reset_index().sort_values('onset')
            for _, row in run_ev[run_ev['event_type'] == 'gabor'].iterrows():
                rows.append(float(row['value']))
    return pd.DataFrame({'x': np.array(rows, dtype=np.float32)})


def main(subject, mask=None, n_iterations=1000, model_type='standard',
         bids_folder=BIDS_FOLDER, fmriprep_deriv='fmriprep',
         smoothed=False, debug=False, allow_incomplete=False):
    bids_folder = Path(bids_folder)
    sub = Subject(subject, bids_folder=bids_folder, fmriprep_deriv=fmriprep_deriv)

    if not allow_incomplete:
        sub.require_complete_sessions()

    # Encoding models are always fitted jointly across ALL of the subject's
    # MRI sessions. The legacy per-session output path was dropped — single
    # session input would silently overwrite the joint fit.
    sessions = sorted(sub.get_sessions())

    if model_type in ('session-shift', 'gauss-session-shift') and len(sessions) < 2:
        raise ValueError(f'--model {model_type} requires at least 2 sessions')

    print(f'sub-{subject}  all-sessions ({sessions})  '
          f'[abstract pRF on objective value  model={model_type}]')

    if debug:
        n_iterations = 50

    # ── paradigm ─────────────────────────────────────────────────────────────
    paradigm = get_value_paradigm(sub, sessions)
    value_min = float(paradigm['x'].min())
    value_max = float(paradigm['x'].max())
    print(f'  {len(paradigm)} trials  value range: {value_min:.1f}–{value_max:.1f} CHF')

    # ── betas ─────────────────────────────────────────────────────────────────
    betas_img = sub.get_single_trial_estimates(sessions, desc='gabor',
                                               smoothed=smoothed)
    assert betas_img.shape[3] == len(paradigm), (
        f'Beta count mismatch: {betas_img.shape[3]} vs {len(paradigm)}')

    # ── masker ────────────────────────────────────────────────────────────────
    if mask is None:
        mask = sub.get_brain_mask(sessions[0])
    masker = NiftiMasker(mask_img=mask).fit()
    data = pd.DataFrame(masker.transform(betas_img).astype(np.float32))
    print(f'  {data.shape[1]} voxels in mask')

    _skip_save = False
    if debug and data.shape[1] > 1000:
        rng = np.random.default_rng(0)
        debug_cols = rng.choice(data.shape[1], 1000, replace=False)
        data = data.iloc[:, debug_cols]
        _skip_save = True
        print(f'  [debug] subsampled to {data.shape[1]} voxels (saving skipped)')

    # ── model + grid search + gradient descent ────────────────────────────────
    # This is the canonical three-stage braincoder fit:
    #   1. fit_grid() — coarse correlation-cost search over a regular grid
    #   2. refine_baseline_and_amplitude() — closed-form refinement; NEVER skip
    #   3. fit() — Adam gradient descent, init from refined grid
    #
    # The three other model variants (session-shift, gaussian, gauss-session-shift)
    # follow the same pattern with a different braincoder model class. See the
    # provenance file for the full source.

    smooth_label = '_smoothed' if smoothed else ''

    model  = LogGaussianPRF(allow_neg_amplitudes=False, parameterisation='mode_fwhm_natural')
    fitter = ParameterFitter(model, data, paradigm)

    n_mode = 12 if debug else 20
    n_fwhm = 8  if debug else 15
    modes      = np.linspace(value_min, value_max, n_mode).astype(np.float32)
    fwhms      = np.linspace(1.0, value_max - value_min, n_fwhm).astype(np.float32)
    amplitudes = np.array([1.0], dtype=np.float32)
    baselines  = np.array([0.0], dtype=np.float32)

    print(f'  grid search ({n_mode}×{n_fwhm} = {n_mode*n_fwhm} points)...')
    grid_pars = fitter.fit_grid(modes, fwhms, amplitudes, baselines,
                                use_correlation_cost=True)
    grid_pars = fitter.refine_baseline_and_amplitude(grid_pars)

    print(f'  gradient descent ({n_iterations} iterations)...')
    pars = fitter.fit(max_n_iterations=n_iterations, init_pars=grid_pars)

    pred = model.predict(parameters=pars, paradigm=paradigm)
    r2   = get_rsq(data, pred)
    print(f'  mean R²={float(r2.mean()):.4f}')

    if not _skip_save:
        out_dir = (bids_folder / 'derivatives' / 'encoding_models'
                   / 'aprf' / f'sub-{subject}' / 'func')
        out_dir.mkdir(parents=True, exist_ok=True)

        fn = (f'sub-{subject}_task-abstractvalue'
              f'_space-T1w_desc-{{desc}}{smooth_label}_pe.nii.gz')

        for param in ['mode', 'fwhm', 'amplitude', 'baseline']:
            save_f32(masker.inverse_transform(pars[param]),
                     out_dir / fn.format(desc=param))
        save_f32(masker.inverse_transform(r2), out_dir / fn.format(desc='r2'))

        print(f'  saved to {out_dir}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('subject', help="Subject label without 'sub-'")
    parser.add_argument('--model', default='standard',
                        choices=['standard', 'session-shift',
                                 'gaussian', 'gauss-session-shift'],
                        help='Model type (default: standard)')
    parser.add_argument('--mask', default=None,
                        help='Brain mask NIfTI (default: fmriprep brain mask)')
    parser.add_argument('--n-iterations', type=int, default=1000,
                        help='Max gradient descent iterations (default: 1000)')
    parser.add_argument('--bids-folder', default=str(BIDS_FOLDER))
    parser.add_argument('--fmriprep-deriv', default='fmriprep',
                        choices=['fmriprep', 'fmriprep-t2w'])
    parser.add_argument('--smoothed', action='store_true')
    parser.add_argument('--debug', action='store_true',
                        help='Fast local test: 50 iterations, 500 voxels, small grid')
    parser.add_argument('--allow-incomplete', action='store_true',
                        help='Skip the "all expected MRI sessions present" check '
                             '(default: 2 for study subjects, 1 for pilots).')
    args = parser.parse_args()

    main(args.subject, mask=args.mask,
         n_iterations=args.n_iterations, model_type=args.model,
         bids_folder=args.bids_folder, fmriprep_deriv=args.fmriprep_deriv,
         smoothed=args.smoothed, debug=args.debug,
         allow_incomplete=args.allow_incomplete)
