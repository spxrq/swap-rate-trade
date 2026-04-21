"""Tests for synthetic.want.ou_with_noise.

Parameter values here are chosen for test determinism, not realism. The
realistic parameters for a 50Y EUR IRS intraday process live in
docs/PARAMETER_SOURCES.md and are applied in notebooks/.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from statsmodels.tsa.stattools import adfuller

from synthetic.want.ou_with_noise import simulate

START = pd.Timestamp("2024-01-02 08:00", tz="CET")

N_PATHS = 500       # Monte Carlo sample size
ALPHA = 0.05        # ADF significance level
BETA = 0.9          # minimum required power on the want/ DGP


def _simulate(n_minutes: int = 540, seed: int = 0) -> pd.DataFrame:
    return simulate(
        mu=0.045,
        theta=0.05,
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
            mu=0.045,
            theta=0.05,
            sigma_eff=1e-4,
            sigma_noise=5e-5,
            n_minutes=540,
            start=pd.Timestamp("2024-01-02 08:00"),  # naive
            seed=0,
        )


def test_adf_power_on_want_dgp():
    """Monte Carlo: the ADF test must reliably detect mean-reversion on paths
    from the want/ DGP. We require power >= BETA over N_PATHS simulations.

    Rationale: this is the `want/`-side of the project's validation
    principle (see ARCHITECTURE.md). A single-path assertion would pass or
    fail on the luck of the seed; the distributional claim is what matters.
    """
    rejections = 0
    for seed in range(N_PATHS):
        df = _simulate(n_minutes=2000, seed=seed)
        p = adfuller(df["50Y"].values, autolag="AIC")[1]
        if p < ALPHA:
            rejections += 1
    power = rejections / N_PATHS
    assert power >= BETA, (
        f"ADF power {power:.3f} below target {BETA} "
        f"over {N_PATHS} paths at alpha={ALPHA}"
    )
