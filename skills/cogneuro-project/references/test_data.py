# ============================================================================
# REAL EXEMPLAR — verbatim from a working project.
#
# Provenance: ~/git/tms_risk/tests/test_data.py @ aca7c4d
#
# What to study:
#   * Tests run against LIVE BIDS, not a mock. The Subject class's whole job
#     is to encode on-disk layout — a mock would just re-encode the layout in
#     the test and prove nothing.
#   * The `bids_folder` fixture `pytest.skip(...)` if the data isn't present
#     (fresh clone, CI, away from the cluster) — keeps the suite useful in
#     both contexts.
#   * Path comes from env var with a default (TMS_RISK_BIDS); flexible per
#     setup, no hardcoded path.
#   * `test_subject_constructs` exercises both Subject(int) and Subject(str)
#     so the type-tolerant constructor doesn't drift.
#   * `test_outliers_constant` codifies a published exclusion list (de
#     Hollander, Moisa & Ruff 2024) — would surface a regression if someone
#     edited the outlier list and forgot a paper.
#   * `test_get_all_behavior_returns_dataframe` asserts the columns
#     downstream code depends on ('n1', 'n2', 'choice', 'rt') — turns
#     implicit column contracts into explicit tests.
#   * `test_get_data_for_flexible_label` exercises the model-aware data prep
#     (boolean choice column) — catches drift between data layer and model
#     dispatch.
#
# This file does NOT yet include the NIfTI dtype guard test (round-trip
# 64-distinct-value array through _write_volume to confirm no quantization).
# Worth adding to any new project's test_data.py — the bug burns repeatedly
# and is catastrophically silent. See ~/.claude/CLAUDE.md "NIfTI dtype trap".
# ============================================================================
"""Smoke tests for the Subject class — single source of truth for data access.

These tests run against the live BIDS dataset (if present) rather than a
mock, because the Subject class's main responsibility is to correctly
encode the on-disk layout. Tests are skipped when the data isn't
available — typical on a fresh clone, on CI, or away from the cluster.

Run locally with::

    conda activate tms_risk
    pytest tests/

A failed test almost certainly means the dataset has shifted (new file
naming, missing run, etc.); a passing test does not guarantee the rest
of the pipeline runs end-to-end.
"""
import os
from pathlib import Path

import pytest


BIDS_FOLDER = os.environ.get('TMS_RISK_BIDS', '/data/ds-tmsrisk')


@pytest.fixture(scope='module')
def bids_folder():
    folder = Path(BIDS_FOLDER)
    if not folder.exists():
        pytest.skip(f'BIDS folder {folder} not present')
    if not (folder / 'participants.tsv').exists():
        pytest.skip(f'No participants.tsv in {folder}')
    return str(folder)


def test_outliers_constant(bids_folder):
    """Outlier list must include 22 and 49 (de Hollander, Moisa & Ruff 2024)."""
    from tms_risk.utils.data import get_tms_subjects

    excluded = set(get_tms_subjects(bids_folder=bids_folder, exclude_outliers=False))
    kept = set(get_tms_subjects(bids_folder=bids_folder, exclude_outliers=True))
    dropped = excluded - kept
    assert 22 in dropped, '22 should be flagged as outlier'
    assert 49 in dropped, '49 should be flagged as outlier'


def test_subject_constructs(bids_folder):
    """Subject(int) and Subject(str) should both work; zero-padding is internal."""
    from tms_risk.utils.data import Subject

    s_int = Subject(1, bids_folder=bids_folder)
    s_str = Subject('01', bids_folder=bids_folder)
    # Just confirm both constructed without exception
    assert s_int is not None
    assert s_str is not None


def test_get_all_behavior_returns_dataframe(bids_folder):
    """get_all_behavior should return a non-empty DataFrame with the
    cross-cutting columns the cognitive models read."""
    import pandas as pd
    from tms_risk.utils.data import get_all_behavior

    df = get_all_behavior(bids_folder=bids_folder, all_tms_conditions=True,
                          exclude_outliers=True)
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0
    for col in ('n1', 'n2', 'choice', 'rt'):
        assert col in df.columns, f'missing column {col!r}'


def test_outliers_actually_dropped_from_behavior(bids_folder):
    """Behavior df with exclude_outliers=True should contain neither
    sub-22 nor sub-49."""
    from tms_risk.utils.data import get_all_behavior

    df = get_all_behavior(bids_folder=bids_folder, all_tms_conditions=True,
                          exclude_outliers=True)
    if 'subject' in df.index.names:
        present = set(df.index.get_level_values('subject').astype(int).unique())
    else:
        present = set(df['subject'].astype(int).unique())
    assert 22 not in present
    assert 49 not in present


def test_get_data_for_flexible_label():
    """fit_model.get_data must produce a frame with 'choice' as bool-ish
    after the model-label-specific massaging."""
    if not Path(BIDS_FOLDER).exists():
        pytest.skip('BIDS folder not present')
    from tms_risk.behavior.fit_model import get_data

    df = get_data(bids_folder=BIDS_FOLDER, model_label='flexible2.6')
    assert 'choice' in df.columns
    # `choice == 2.0` → bool/0-1
    assert df['choice'].dtype in (bool, 'bool', int, 'int64', 'int32')
