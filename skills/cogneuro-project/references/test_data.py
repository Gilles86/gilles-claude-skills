"""Smoke tests for the Subject class — catches regressions in path
resolution, per-subject quirks, and (most importantly) the NIfTI
dtype guard.

Run: pytest tests/test_data.py
"""
from __future__ import annotations

from pathlib import Path

import nibabel as nib
import numpy as np
import pandas as pd
import pytest

from <package>.utils.data import Subject, select_well_fit_voxels


# --- Subject identity / id parsing ---

@pytest.mark.parametrize('inp,expected', [
    (1, '01'),
    (15, '15'),
    ('1', '01'),
    ('01', '01'),
    ('pil01', 'pil01'),
])
def test_subject_id_normalization(inp, expected, tmp_path):
    sub = Subject(inp, bids_folder=tmp_path)
    assert sub.subject_id == expected


def test_pilot_flag(tmp_path):
    assert Subject('pil01', bids_folder=tmp_path).is_pilot is True
    assert Subject(1, bids_folder=tmp_path).is_pilot is False


def test_sub_property(tmp_path):
    assert Subject(1, bids_folder=tmp_path).sub == 'sub-01'
    assert Subject('pil02', bids_folder=tmp_path).sub == 'sub-pil02'


# --- subjects.yml-driven metadata ---

def test_get_runs_default(tmp_path):
    """Subject with no override falls back to runs 1..8 (per skeleton default)."""
    sub = Subject(1, bids_folder=tmp_path)
    # Adjust if your project's default differs.
    assert sub.get_runs(session=1) == [1, 2, 3, 4, 5, 6, 7, 8]


# --- Subject quirks (REPLACE per project) ---

def test_quirky_subject_branches(tmp_path):
    """Add a test for every branch in Subject._apply_*_quirks().

    Catches regressions where a refactor accidentally drops a fix
    (e.g., the sub-06 ses-2 run-5 pulse-t0 shift in retinonumeral).
    """
    pytest.skip('Add tests for project-specific quirks')


# --- select_well_fit_voxels ---

def test_select_well_fit_voxels_filters_low_r2():
    df = pd.DataFrame({
        'r2': [0.10, 0.02, 0.20],
        'sigma': [1.0, 1.0, 1.0],
        'x': [0.0, 0.0, 0.0],
        'y': [0.0, 0.0, 0.0],
    })
    out = select_well_fit_voxels(df, r2_threshold=0.05)
    assert len(out) == 2
    assert (out['r2'] > 0.05).all()


def test_select_well_fit_voxels_filters_outside_aperture():
    df = pd.DataFrame({
        'r2': [0.10, 0.10],
        'sigma': [1.0, 1.0],
        'x': [0.0, 5.0],   # second is outside default aperture (3.17°)
        'y': [0.0, 0.0],
    })
    out = select_well_fit_voxels(df)
    assert len(out) == 1
    assert out.iloc[0]['x'] == 0.0


# --- NIfTI dtype guard (the most important test) ---

def test_write_volume_uses_float32(tmp_path):
    """Subject._write_volume must produce float32 NIfTI even when the mask
    is uint8 (the default for fmriprep brain masks).

    Without the guard, output inherits uint8 + scl_slope, quantizing
    to ~256 values across all voxels. This test injects 64 distinct
    floats and checks all 64 survive the round-trip.
    """
    from nilearn.maskers import NiftiMasker

    # Build a uint8 mask (mimics fmriprep brain_mask)
    mask_data = np.ones((4, 4, 4), dtype=np.uint8)
    mask_img = nib.Nifti1Image(mask_data, affine=np.eye(4))
    masker = NiftiMasker(mask_img=mask_img).fit()

    # 64 distinct float values
    values = np.linspace(-3.14, 2.71, 64).astype(np.float32)

    sub = Subject(1, bids_folder=tmp_path)
    out_path = tmp_path / 'test_out.nii.gz'
    sub._write_volume(values, masker, out_path)

    written = nib.load(out_path)
    assert written.get_data_dtype() == np.float32
    assert written.header['scl_slope'] == 1
    assert written.header['scl_inter'] == 0
    assert len(np.unique(written.get_fdata())) == 64
