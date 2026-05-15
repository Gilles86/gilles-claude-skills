"""Subject class skeleton — single source of truth for BIDS data access.

Copy to <package>/utils/data.py and adapt. The class encapsulates:
- Path resolution (local vs cluster, sub-XX vs sub-pilXX)
- BIDS file naming
- Per-subject quirks (early pilots, bugged runs, missing sessions)
- NIfTI dtype-safe writes via _write_volume()

Analysis scripts import Subject; they NEVER build BIDS paths directly.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import nibabel as nib
import numpy as np
import pandas as pd
import yaml
from nilearn.maskers import NiftiMasker


# --- Module-level constants (importable by downstream code) ---

DEFAULT_BIDS_FOLDER = Path('/data/ds-<project>')
CLUSTER_BIDS_FOLDER = Path('/shares/zne.uzh/gdehol/ds-<project>')

# Per-experiment geometry — override per project. Example from retsupp:
# DISTRACTOR_LOCATIONS = {
#     'upper_right': (2.83, 2.83), 'upper_left': (-2.83, 2.83),
#     'lower_right': (2.83, -2.83), 'lower_left': (-2.83, -2.83),
# }


# --- Helpers ---

@lru_cache(maxsize=1)
def _load_subjects_yml() -> dict:
    """Lazy-load <package>/data/subjects.yml. Cached after first call.

    Lazy so `from <package>.utils.data import Subject` doesn't crash
    if subjects.yml is missing or malformed; the error surfaces only
    when a Subject actually queries metadata.
    """
    here = Path(__file__).resolve().parent.parent
    with open(here / 'data' / 'subjects.yml') as f:
        return yaml.safe_load(f) or {}


# --- Subject ---

class Subject:
    """fMRI + behavior accessor for a single BIDS participant.

    Parameters
    ----------
    subject_id : int or str
        Numeric or zero-padded string ('01'). Pilots are strings ('pil01').
    bids_folder : str or Path, optional
        BIDS root. Defaults to local mac path; SLURM scripts override
        to /shares/zne.uzh/gdehol/ds-<project>.
    """

    def __init__(self, subject_id, bids_folder=DEFAULT_BIDS_FOLDER):
        if isinstance(subject_id, int):
            self.subject_id = f'{subject_id:02d}'
            self.is_pilot = False
        elif isinstance(subject_id, str) and subject_id.startswith('pil'):
            self.subject_id = subject_id
            self.is_pilot = True
        else:
            self.subject_id = f'{int(subject_id):02d}'
            self.is_pilot = False

        self.bids_folder = Path(bids_folder)

    @property
    def _meta(self) -> dict:
        return _load_subjects_yml().get(self.subject_id, {})

    # --- Identity ---

    @property
    def sub(self) -> str:
        """BIDS subject label, e.g. 'sub-01' or 'sub-pil01'."""
        return f'sub-{self.subject_id}'

    @property
    def fmriprep_root(self) -> Path:
        return self.bids_folder / 'derivatives' / 'fmriprep' / self.sub

    # --- Metadata (sessions, runs) ---

    def get_sessions(self) -> list[int]:
        """Session numbers from subjects.yml; defaults to [1]."""
        return list(self._meta.get('sessions', [1]))

    def get_runs(self, session: int) -> list[int]:
        """Run numbers for a session.

        subjects.yml schema: {sub-id: {runs: {1: [1,2,...]}, ...}}.
        Default if unspecified: range(1, 9) — adjust per project.
        """
        runs_meta = self._meta.get('runs', {})
        if session in runs_meta:
            return list(runs_meta[session])
        return list(range(1, 9))

    # --- BOLD access ---

    def get_preprocessed_bold(
        self,
        session: int,
        run: int | None = None,
        space: str = 'T1w',
    ) -> list[Path]:
        """Paths to fmriprep-preprocessed BOLD NIfTIs."""
        runs = [run] if run is not None else self.get_runs(session)
        return [
            self.fmriprep_root / f'ses-{session}' / 'func' /
            f'{self.sub}_ses-{session}_task-<task>_run-{r}_'
            f'space-{space}_desc-preproc_bold.nii.gz'
            for r in runs
        ]

    def get_single_trial_estimates(
        self,
        session: int,
        kind: str = 'stim',
        smoothed: bool = False,
        roi: str | None = None,
    ):
        """GLMsingle single-trial beta NIfTI (one volume per trial).

        If roi is given, returns a (n_trials, n_voxels) array via the ROI
        masker; otherwise returns the NIfTI image.
        """
        deriv = 'glmsingle.smoothed' if smoothed else 'glmsingle'
        path = (
            self.bids_folder / 'derivatives' / deriv / self.sub
            / f'ses-{session}' / 'func'
            / f'{self.sub}_ses-{session}_desc-{kind}_betas.nii.gz'
        )
        img = nib.load(path)
        if roi is not None:
            masker = self.get_volume_mask(roi=roi, return_masker=True)
            return masker.transform(img)
        return img

    # --- PRF / encoding-model parameters ---
    # NOTE: split into two methods. Don't return "DataFrame OR dict" from one.

    def get_prf_parameters_tsv(
        self,
        model_label: int,
        smoothed: bool = False,
    ) -> pd.DataFrame:
        """Pre-extracted parameter TSV: one row per voxel, columns for each
        parameter (amplitude, mu, sigma, r2). Fast — use for plotting/stats.
        """
        suffix = '.smoothed' if smoothed else ''
        tsv = (
            self.bids_folder / 'derivatives' / f'extracted_pars{suffix}'
            / f'{self.sub}_model-{model_label}_pars.tsv'
        )
        return pd.read_csv(tsv, sep='\t', index_col=0)

    def get_prf_parameters_volume(
        self,
        model_label: int,
        smoothed: bool = False,
    ) -> dict[str, nib.Nifti1Image]:
        """Parameter NIfTIs (one volume per parameter). Use for spatial
        analyses (surface projection, ROI overlays).
        """
        deriv = 'modeling.smoothed' if smoothed else 'modeling'
        base = (
            self.bids_folder / 'derivatives' / deriv / self.sub
            / 'func' / f'{self.sub}_model-{model_label}'
        )
        return {
            p: nib.load(f'{base}_desc-{p}_pe.nii.gz')
            for p in ('amplitude', 'mu', 'sigma', 'r2')
        }

    # --- Masks ---

    def get_brain_mask(
        self,
        session: int | None = None,
        return_masker: bool = True,
    ):
        """Whole-brain mask from fmriprep (T1w space)."""
        ses = session if session is not None else self.get_sessions()[0]
        path = (
            self.fmriprep_root / f'ses-{ses}' / 'func'
            / f'{self.sub}_ses-{ses}_task-<task>_'
            f'space-T1w_desc-brain_mask.nii.gz'
        )
        img = nib.load(path)
        return NiftiMasker(mask_img=img).fit() if return_masker else img

    def get_volume_mask(
        self,
        roi: str,
        return_masker: bool = False,
    ):
        """ROI mask in T1w space. roi e.g. 'V1_L', 'NPCr'."""
        path = (
            self.bids_folder / 'derivatives' / 'masks' / self.sub
            / f'{self.sub}_desc-{roi}_mask.nii.gz'
        )
        img = nib.load(path)
        return NiftiMasker(mask_img=img).fit() if return_masker else img

    # --- Behavior + events ---

    def get_onsets(self, session: int, run: int | None = None) -> pd.DataFrame:
        """Trial onsets from BIDS events.tsv (one row per trial)."""
        runs = [run] if run is not None else self.get_runs(session)
        dfs = []
        for r in runs:
            tsv = (
                self.bids_folder / self.sub / f'ses-{session}' / 'func'
                / f'{self.sub}_ses-{session}_task-<task>_run-{r}_events.tsv'
            )
            df = pd.read_csv(tsv, sep='\t')
            df['session'] = session
            df['run'] = r
            df = self._apply_onset_quirks(df, session, r)
            dfs.append(df)
        return pd.concat(dfs, ignore_index=True)

    def _apply_onset_quirks(self, df: pd.DataFrame, session: int, run: int):
        """Per-subject onset fixes. Document each here, never inline in scripts.

        Example (retinonumeral sub-06 ses-2 run-5):
            if self.subject_id == '06' and session == 2 and run == 5:
                # First TR pulse missing in scanner log — shift onsets by 1 TR
                df = df.copy()
                df['onset'] -= TR
        """
        return df

    def get_behavioral_data(
        self,
        session: int | None = None,
        tasks: list[str] | None = None,
    ) -> pd.DataFrame:
        """All behavioral trials, optionally filtered. MultiIndex on
        (subject, session, run, trial_nr). Override per project — task-specific.
        """
        raise NotImplementedError('Override in project — task-specific.')

    # --- Confounds ---

    def get_confounds(
        self,
        session: int,
        kind: str = 'minimum',
    ) -> pd.DataFrame:
        """fMRIprep motion / acquisition regressors.

        kind: 'minimum' (6 motion + outliers) | 'full' (CompCor too).
        """
        raise NotImplementedError

    # --- Writers (dtype-safe) ---

    def _write_volume(
        self,
        values: np.ndarray,
        masker: NiftiMasker,
        path: str | Path,
    ) -> None:
        """Write a derived parameter NIfTI safely.

        Without this guard, masker.inverse_transform().to_filename()
        inherits the (uint8) mask dtype and quantizes all parameters to
        ~256 values via scl_slope. See ~/.claude/CLAUDE.md "NIfTI dtype
        trap".
        """
        img = masker.inverse_transform(values)
        img.set_data_dtype(np.float32)
        img.header.set_slope_inter(slope=1, inter=0)
        img.to_filename(str(path))


# --- Standalone voxel-selection helper ---

def select_well_fit_voxels(
    df: pd.DataFrame,
    *,
    r2_threshold: float = 0.05,
    sigma_floor: float = 0.30,
    sigma_ceil: float = 4.0,
    aperture_radius: float = 3.17,
) -> pd.DataFrame:
    """Canonical voxel filter: R², PRF size bounds, PRF center inside aperture."""
    keep = (
        (df['r2'] > r2_threshold)
        & (df['sigma'].between(sigma_floor, sigma_ceil))
        & (np.hypot(df['x'], df['y']) < aperture_radius)
    )
    return df.loc[keep].copy()
