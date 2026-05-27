# ============================================================================
# REAL EXEMPLAR — verbatim from a working project.
#
# Provenance: ~/git/abstract_values/abstract_values/utils/data.py @ a71c630
#             (UZH abstract values fMRI; Gabor-orientation → CHF value learning)
#
# What to study:
#   * __init__ accepts int, '01', or 'pil*'; bids_folder defaults to a module
#     constant the SLURM script can override (--bids-folder).
#   * Private path helpers (_fmriprep_dir, _func_dir, _behavior_dir): all BIDS
#     path construction lives in ONE class. Analysis scripts never build paths.
#   * require_complete_sessions: hard-fail loudly on incomplete subjects
#     instead of silently mis-aggregating downstream.
#   * get_brain_mask: explicitly casts the on-disk uint8 mask to float32 before
#     returning — necessary so that NiftiMasker.inverse_transform() writes
#     parameter NIfTIs as float, not uint8 (see ~/.claude/CLAUDE.md
#     "NIfTI dtype trap"). The project's downstream writers also enforce
#     float32 + slope=1 explicitly.
#   * get_single_trial_estimates: sanity-checks volume count vs expected
#     trials. Catches stale single-session output sitting at the all-sessions
#     path — a recurring footgun.
#   * Separate methods for tabular vs NIfTI returns
#     (get_fisher_information returns DataFrame; get_prf_parameters returns
#     dict of NIfTI images). Never return "DataFrame or dict" from one method.
#   * ROI mask access via get_roi_mask(roi, hemi=...) — the hemi entity is
#     optional (some ROIs are bilateral / unsplit).
# ============================================================================

import re
from pathlib import Path

import nibabel as nib
import numpy as np
import pandas as pd
from nilearn import image

BIDS_FOLDER = Path('/data/ds-abstractvalue')


class Subject:
    """Data access for a single abstract-values fMRI subject.

    Parameters
    ----------
    subject_id : str
        Subject label without the 'sub-' prefix, e.g. ``'pil01'`` or ``'01'``.
    bids_folder : str or Path
    fmriprep_deriv : str
        Which fmriprep derivative folder to use for locating preprocessed BOLD,
        confounds, and brain masks.  Defaults to ``'fmriprep'`` (T1w + T2w).
    """

    def __init__(self, subject_id, bids_folder=BIDS_FOLDER,
                 fmriprep_deriv='fmriprep'):
        self.subject_id = str(subject_id)
        self.bids_folder = Path(bids_folder)
        self.fmriprep_deriv = fmriprep_deriv

    # ── private helpers ────────────────────────────────────────────────────────

    @property
    def _fmriprep_dir(self):
        return self.bids_folder / 'derivatives' / self.fmriprep_deriv

    def _func_dir(self, session):
        return (self._fmriprep_dir / f'sub-{self.subject_id}'
                / f'ses-{session}' / 'func')

    def _behavior_dir(self, session):
        return (self.bids_folder / 'sourcedata' / 'behavior'
                / f'sub-{self.subject_id}' / f'ses-{session}')

    # ── sessions ───────────────────────────────────────────────────────────────

    def get_mapping(self, session):
        """Return value-orientation mapping name for this subject and session.

        The assignment alternates by subject parity:
          Even subject number → ses-1 = 'cdf',         ses-2 = 'inverse_cdf'
          Odd  subject number → ses-1 = 'inverse_cdf', ses-2 = 'cdf'

        Returns
        -------
        str
            ``'cdf'`` or ``'inverse_cdf'``
        """
        num = int(''.join(c for c in self.subject_id if c.isdigit()))
        if num % 2 == 0:
            return 'cdf' if session == 1 else 'inverse_cdf'
        return 'inverse_cdf' if session == 1 else 'cdf'

    def get_sessions(self):
        """Return sorted list of session numbers available in fmriprep output."""
        sub_dir = self._fmriprep_dir / f'sub-{self.subject_id}'
        sessions = []
        for d in sub_dir.iterdir():
            m = re.match(r'ses-(\d+)$', d.name)
            if d.is_dir() and m:
                sessions.append(int(m.group(1)))
        sessions = sorted(sessions)
        if not sessions:
            raise FileNotFoundError(f'No sessions found in {sub_dir}')
        return sessions

    # Study subjects (sub-NN) are expected to have 2 MRI sessions; pilots (sub-pilNN)
    # have 1. Encoding / decoding / FI scripts rely on multi-session aggregation in
    # GLMsingle output paths, so they break silently if started before all sessions
    # are present. Hard-fail loudly instead.
    DEFAULT_EXPECTED_SESSIONS = 2
    PILOT_EXPECTED_SESSIONS = 1

    def expected_sessions(self):
        return (self.PILOT_EXPECTED_SESSIONS
                if self.subject_id.startswith('pil')
                else self.DEFAULT_EXPECTED_SESSIONS)

    def require_complete_sessions(self, expected=None):
        """Raise if fewer than `expected` MRI sessions are present in fmriprep output.

        Defaults: 2 for study subjects, 1 for pilots (`sub-pil*`). Pass `expected`
        to override (e.g. for legitimate single-session debug runs).
        """
        expected = expected if expected is not None else self.expected_sessions()
        sessions = self.get_sessions()
        if len(sessions) < expected:
            raise RuntimeError(
                f'sub-{self.subject_id} has only {len(sessions)} of {expected} '
                f'expected MRI sessions in fmriprep ({sessions}). Refusing to '
                f'run downstream analysis on an incomplete subject — ingest the '
                f'remaining session(s) first, or pass --allow-incomplete.'
            )

    # ── runs ───────────────────────────────────────────────────────────────────

    def get_runs(self, session):
        """Return sorted list of run numbers found in the behavior directory."""
        behavior_dir = self._behavior_dir(session)
        runs = sorted({
            int(re.search(r'run-(\d+)', f.name).group(1))
            for f in behavior_dir.glob(f'*_run-*_task-estimate.*_events.tsv')
        })
        if not runs:
            raise FileNotFoundError(f'No events files found in {behavior_dir}')
        return runs

    # ── BOLD ───────────────────────────────────────────────────────────────────

    def get_preprocessed_bold(self, session, runs=None):
        """Return list of preprocessed BOLD Paths (T1w space)."""
        if runs is None:
            runs = self.get_runs(session)
        func_dir = self._func_dir(session)
        paths = []
        for run in runs:
            matches = sorted(func_dir.glob(
                f'sub-{self.subject_id}_ses-{session}'
                f'_task-abstractvalue_run-{run}_space-T1w_*desc-preproc_bold.nii.gz'
            ))
            if not matches:
                raise FileNotFoundError(
                    f'No BOLD file for run-{run} in {func_dir}')
            paths.append(matches[0])
        return paths

    # ── events ─────────────────────────────────────────────────────────────────

    def get_events(self, session, runs=None):
        """Return gabor and response_bar events for all runs.

        Returns a DataFrame indexed by (run, trial_nr) with columns:
        onset, event_type, orientation, value, response, duration.
        """
        if runs is None:
            runs = self.get_runs(session)

        dfs = []
        for run in runs:
            behavior_dir = self._behavior_dir(session)
            candidates = sorted(behavior_dir.glob(
                f'*_run-{run:02d}_task-estimate.*_events.tsv'))
            if not candidates:
                raise FileNotFoundError(
                    f'No events file for sub-{self.subject_id} '
                    f'ses-{session} run-{run:02d} in {behavior_dir}')
            df = pd.read_csv(candidates[0], sep='\t')

            # Set the first scanner trigger (pulse) as t=0.
            # Raw onsets are relative to Psychopy script start; the BOLD
            # acquisition starts at the first pulse, so we must subtract it.
            pulse_onsets = df.loc[df['event_type'] == 'pulse', 'onset']
            if pulse_onsets.empty:
                raise ValueError(
                    f'No pulse events found in {candidates[0]}')
            first_pulse = float(pulse_onsets.min())
            df = df.copy()
            df['onset'] = df['onset'] - first_pulse

            # The participant's bid is stored in the feedback event, not in
            # response_bar. Join it onto response_bar rows by trial_nr.
            bids = (df[df['event_type'] == 'feedback']
                    .set_index('trial_nr')['response']
                    .rename('bid'))
            df = df[df['event_type'].isin(['gabor', 'response_bar'])].copy()
            df = df.join(bids, on='trial_nr')
            # For response_bar events use the bid; for gabor events it is NaN
            # (intentionally — make_condition_label only uses bid for response_bar).
            df['run'] = run
            dfs.append(df)

        events = pd.concat(dfs, ignore_index=True)
        events = events.set_index(['run', 'trial_nr'])
        return events[['onset', 'event_type', 'orientation', 'value',
                        'bid', 'duration']]

    # ── confounds ──────────────────────────────────────────────────────────────

    def get_confounds(self, session, runs=None,
                      columns=('cosine00', 'cosine01', 'cosine02',
                               'trans_x', 'trans_y', 'trans_z',
                               'rot_x', 'rot_y', 'rot_z')):
        """Return confound timeseries for all runs.

        Returns a DataFrame indexed by (run, timepoint).
        """
        if runs is None:
            runs = self.get_runs(session)
        func_dir = self._func_dir(session)
        dfs = []
        for run in runs:
            fn = (func_dir /
                  f'sub-{self.subject_id}_ses-{session}'
                  f'_task-abstractvalue_run-{run}'
                  f'_desc-confounds_timeseries.tsv')
            if not fn.exists():
                raise FileNotFoundError(f'No confounds file: {fn}')
            df = pd.read_csv(fn, sep='\t')
            available = [c for c in columns if c in df.columns]
            dfs.append(df[available])
        return pd.concat(dfs, keys=runs, names=['run'])

    # ── brain mask ─────────────────────────────────────────────────────────────

    def get_brain_mask(self, session, run=1):
        """Return brain mask NIfTI image (T1w space) from a given run.

        Returned as float32 so that NiftiMasker.inverse_transform produces
        float images rather than inheriting the on-disk uint8 dtype.
        """
        func_dir = self._func_dir(session)
        fn = (func_dir /
              f'sub-{self.subject_id}_ses-{session}'
              f'_task-abstractvalue_run-{run}_space-T1w_desc-brain_mask.nii.gz')
        if not fn.exists():
            raise FileNotFoundError(f'No brain mask: {fn}')
        mask = image.load_img(str(fn))
        return nib.Nifti1Image(mask.get_fdata().astype(np.float32), mask.affine)

    # ── ROI masks ──────────────────────────────────────────────────────────────

    def get_roi_mask(self, roi, hemi='LR'):
        """Return a volumetric ROI mask (T1w space).

        Masks are created by ``get_surface_roi_mask.py`` and stored under
        ``derivatives/masks/sub-{subject}/anat/``.

        Parameters
        ----------
        roi : str
            ROI label, e.g. ``'BensonV1'``, ``'NPC'``.
        hemi : str or None
            Hemisphere entity: ``'LR'`` (bilateral, default), ``'L'``, ``'R'``,
            or ``None`` to omit the hemi entity (used by some ROIs such as NPC).
        """
        mask_dir = (self.bids_folder / 'derivatives' / 'masks'
                    / f'sub-{self.subject_id}' / 'anat')
        if hemi:
            fn = mask_dir / f'sub-{self.subject_id}_space-T1w_hemi-{hemi}_desc-{roi}_mask.nii.gz'
        else:
            fn = mask_dir / f'sub-{self.subject_id}_space-T1w_desc-{roi}_mask.nii.gz'
        if not fn.exists():
            raise FileNotFoundError(f'No ROI mask: {fn}')
        return image.load_img(str(fn))

    # ── GLMsingle outputs ──────────────────────────────────────────────────────

    def get_single_trial_estimates(self, sessions, desc='gabor', smoothed=False,
                                   zscore_sessions=False):
        """Return single-trial beta image from GLMsingle.

        GLMsingle is fitted once across all sessions. Output path::

            derivatives/glmsingle[.smoothed]/sub-{subject}/func/
                sub-{subject}_task-abstractvalue_space-T1w_desc-{desc}_pe.nii.gz

        When ``sessions`` is a strict subset of all sessions, the full image is
        loaded and only the trials belonging to the requested sessions are
        returned (trial order: session → run → gabor event sorted by onset).

        Parameters
        ----------
        sessions : int or list of int
        desc : {'gabor', 'response', 'R2'}
        smoothed : bool
            Load from ``glmsingle.smoothed`` instead of ``glmsingle``.
        zscore_sessions : bool
            Z-score betas within each session before returning.
            Requires multiple sessions.
        """
        if isinstance(sessions, int):
            sessions = [sessions]
        sessions = sorted(sessions)

        glmsingle_deriv = 'glmsingle.smoothed' if smoothed else 'glmsingle'
        sub_dir = (self.bids_folder / 'derivatives' / glmsingle_deriv
                   / f'sub-{self.subject_id}')

        fn = (sub_dir / 'func'
              / f'sub-{self.subject_id}_task-abstractvalue'
                f'_space-T1w_desc-{desc}_pe.nii.gz')

        if not fn.exists():
            raise FileNotFoundError(
                f'No GLMsingle output ({desc}) for sub-{self.subject_id}: {fn}\n'
                f'Run fit_glmsingle.sh ({"smoothed" if smoothed else "unsmoothed"}) '
                f'for all sessions.')

        im = image.load_img(str(fn))

        # ── sanity-check volume count ─────────────────────────────────────────
        # Compute expected trial count for *all* sessions so we can warn early
        # when a stale single-session file sits at the canonical all-sessions path.
        all_sessions = sorted(self.get_sessions())
        expected_total = 0
        for ses in all_sessions:
            runs = self.get_runs(ses)
            events = self.get_events(ses, runs)
            for run in runs:
                run_ev = events.loc[run].reset_index().sort_values('onset')
                expected_total += len(run_ev[run_ev['event_type'] == 'gabor'])
        if im.shape[3] < expected_total and sessions == all_sessions:
            raise ValueError(
                f'Loaded {im.shape[3]} volumes from {fn} but expected '
                f'{expected_total} (all {len(all_sessions)} sessions). '
                f'The file may be a stale single-session output. '
                f'Re-run GLMsingle ({"smoothed" if smoothed else "unsmoothed"}) '
                f'for all sessions and it will overwrite this file.')

        # ── session subsetting ────────────────────────────────────────────────
        # When loading the all-sessions image but only a subset is requested,
        # select the matching trial indices.
        if sessions != all_sessions:
            trial_indices = []
            cumulative = 0
            for ses in all_sessions:
                runs = self.get_runs(ses)
                events = self.get_events(ses, runs)
                for run in runs:
                    run_ev = events.loc[run].reset_index().sort_values('onset')
                    n = len(run_ev[run_ev['event_type'] == 'gabor'])
                    if ses in sessions:
                        trial_indices.extend(range(cumulative, cumulative + n))
                    cumulative += n
            im = image.index_img(im, trial_indices)

        # ── per-session z-scoring ─────────────────────────────────────────────
        if zscore_sessions:
            if len(sessions) < 2:
                raise ValueError('zscore_sessions requires multiple sessions')
            session_sizes = []
            for ses in sessions:
                runs = self.get_runs(ses)
                events = self.get_events(ses, runs)
                n = sum(
                    len(events.loc[run].reset_index()
                        .query("event_type == 'gabor'"))
                    for run in runs
                )
                session_sizes.append(n)
            boundaries = np.cumsum([0] + session_sizes)
            zscored = []
            for start, stop in zip(boundaries[:-1], boundaries[1:]):
                block = image.index_img(im, slice(start, stop))
                zscored.append(image.clean_img(block, detrend=False,
                                               standardize='zscore'))
            im = image.concat_imgs(zscored)

        return im

    def get_glmsingle_betas(self, sessions, desc='gabor'):
        """Alias for get_single_trial_estimates (smoothed=False)."""
        return self.get_single_trial_estimates(sessions, desc=desc)

    # ── encoding model outputs ─────────────────────────────────────────────────
    # NOTE: separate methods for tabular vs NIfTI returns. Never return
    # "DataFrame or dict" from a single method — split them.

    def get_fisher_information(self, session=None, roi='BensonV1', hemi='LR',
                               n_voxels=250, smoothed=False):
        """Return Fisher information DataFrame computed by compute_fisher_information.py.

        Index is orientation in **degrees**; column is ``fisher_information``.

        Parameters
        ----------
        session : int or None
            Session number.  ``None`` loads the across-session fit (no ses- dir).
        roi : str
        hemi : str or None
            ``'LR'``, ``'L'``, ``'R'``, or ``None`` (omit hemi entity).
        n_voxels : int
        smoothed : bool
        """
        hemi_arg = None if hemi == 'None' else hemi
        mask_desc = f'{roi}{"_hemi-" + hemi if hemi_arg else ""}'
        smooth_label = '_smoothed' if smoothed else ''

        ses_dir    = f'ses-{session}' if session is not None else ''
        ses_entity = f'_ses-{session}' if session is not None else ''

        out_dir = (self.bids_folder / 'derivatives' / 'encoding_models' / 'vonmises'
                   / f'sub-{self.subject_id}')
        if ses_dir:
            out_dir = out_dir / ses_dir
        out_dir = out_dir / 'func'

        fn = (out_dir /
              f'sub-{self.subject_id}{ses_entity}_task-abstractvalue'
              f'_mask-{mask_desc}_nvoxels-{n_voxels}{smooth_label}_desc-fisherinfo_pe.tsv')

        if not fn.exists():
            raise FileNotFoundError(f'No Fisher information file: {fn}')

        df = pd.read_csv(fn, sep='\t', index_col=0)
        df.index = np.rad2deg(df.index)
        return df

    def get_prf_parameters(self, sessions=None, smoothed=False):
        """Return dict of NIfTI images for fitted aPRF parameters.

        Keys: ``'mode'``, ``'fwhm'``, ``'amplitude'``, ``'baseline'``, ``'r2'``.

        The aPRF (LogGaussianPRF) is always fitted jointly across all of a
        subject's sessions; outputs live at
        ``derivatives/encoding_models/aprf/sub-<subject>/func/`` with no
        ``ses-*`` entity in the path or filename.

        Parameters
        ----------
        sessions : ignored (kept for backwards compatibility with old callers).
            Per-session aPRF fits were dropped; the joint fit is now the only
            output and this parameter has no effect on the path returned.
        smoothed : bool
        """
        del sessions  # legacy: per-session fits no longer exist
        smooth_label = '_smoothed' if smoothed else ''

        out_dir = (self.bids_folder / 'derivatives' / 'encoding_models' / 'aprf'
                   / f'sub-{self.subject_id}' / 'func')

        result = {}
        for param in ['mode', 'fwhm', 'amplitude', 'baseline', 'r2']:
            fn = (out_dir / f'sub-{self.subject_id}_task-abstractvalue'
                            f'_space-T1w_desc-{param}{smooth_label}_pe.nii.gz')
            if not fn.exists():
                raise FileNotFoundError(f'No aPRF parameter file: {fn}')
            result[param] = image.load_img(str(fn))
        return result
