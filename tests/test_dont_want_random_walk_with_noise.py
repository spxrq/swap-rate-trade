"""Tests for synthetic.dont_want.random_walk_with_noise.

Parameter values here are chosen for test determinism, not realism.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from statsmodels.tsa.stattools import adfuller

from synthetic.dont_want.random_walk_with_noise import simulate

START = pd.Timestamp("2024-01-02 08:00", tz="CET")

N_PATHS = 500           # Monte Carlo sample size
ALPHA = 0.05            # nominal ADF significance level
FPR_TOLERANCE = 1.5     # finite-sample tolerance on type-I rate


def _simulate(n_minutes: int = 540, seed: int = 0) -> pd.DataFrame:
    return simulate(
        start_level=0.045,
        sigma_eff=1e-4,
        sigma_noise=5e-5,
        n_minutes=n_minutes,
        start=START,
        seed=seed,
    )


def test_shape_matches_contract():
    df = _simulate(n_minutes=540)
    assert isinstance(df.index, pd.DatetimeIndex)
    assert df.index.tz is not None
    assert df.index[0] == START
    assert len(df) == 540
    assert df.columns.tolist() == ["50Y"]
    assert df["50Y"].dtype == np.float64
    assert not df["50Y"].isna().any()


def test_reproducible_with_seed():
    a = _simulate(seed=42)
    b = _simulate(seed=42)
    pd.testing.assert_frame_equal(a, b)


def test_rejects_naive_start_timestamp():
    """Per docs/DATA_CONTRACT.md, `start` must be timezone-aware."""
    with pytest.raises(ValueError, match="timezone-aware"):
        simulate(
            start_level=0.045,
            sigma_eff=1e-4,
            sigma_noise=5e-5,
            n_minutes=540,
            start=pd.Timestamp("2024-01-02 08:00"),  # naive
            seed=0,
        )


def test_adf_false_positive_rate_under_unit_root():
    """Monte Carlo: the ADF test's rejection rate on the null DGP must not
    exceed the nominal significance level (with finite-sample tolerance).

    Rationale: a null DGP is stochastic — at alpha, a properly-sized ADF
    test will reject roughly alpha of the time by construction. A single
    path can false-reject; the distributional guarantee is what matters for
    the project's validation principle (see ARCHITECTURE.md).
    """
    rejections = 0
    for seed in range(N_PATHS):
        df = _simulate(n_minutes=2000, seed=seed)
        p = adfuller(df["50Y"].values, autolag="AIC")[1]
        if p < ALPHA:
            rejections += 1
    fpr = rejections / N_PATHS
    max_allowed = FPR_TOLERANCE * ALPHA
    assert fpr <= max_allowed, (
        f"False-positive rate {fpr:.3f} exceeds max {max_allowed:.3f} "
        f"(= {FPR_TOLERANCE} * alpha) over {N_PATHS} paths"
    )
