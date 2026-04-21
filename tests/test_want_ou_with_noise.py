"""Tests for synthetic.want.ou_with_noise.

Parameter values here are chosen for test determinism, not realism. The
realistic parameters for a 50Y EUR IRS intraday process are an open operator
decision (see docs/IMPLEMENTATION_STATUS.md).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller

from synthetic.want.ou_with_noise import simulate

START = pd.Timestamp("2024-01-02 08:00", tz="CET")


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


def test_series_is_stationary():
    """The want DGP claims mean-reversion: ADF must reject unit root."""
    df = _simulate(n_minutes=2000, seed=0)
    p_value = adfuller(df["50Y"].values, autolag="AIC")[1]
    assert p_value < 0.01, f"Expected rejection of unit root; got p={p_value:.4f}"
