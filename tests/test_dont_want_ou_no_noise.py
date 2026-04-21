"""Tests for synthetic.dont_want.ou_no_noise.

Parameter values here are chosen for test determinism, not realism.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from synthetic.dont_want.ou_no_noise import simulate

START = pd.Timestamp("2024-01-02 08:00", tz="CET")


def _simulate(n_minutes: int = 540, seed: int = 0) -> pd.DataFrame:
    return simulate(
        mu=0.045,
        theta=0.05,
        sigma_eff=1e-4,
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
            n_minutes=540,
            start=pd.Timestamp("2024-01-02 08:00"),  # naive
            seed=0,
        )


def test_single_path_smoke_low_return_autocorr():
    """Single-path smoke test. NOT a validation test.

    Without microstructure noise, 1-lag return autocorrelation should not
    show the strongly-negative signature that iid noise induces. This is a
    weak proxy for 'signature plot is approximately flat' and is retained
    only to catch gross breakage.

    TODO: replace with a proper Monte Carlo type-I test against a real
    RV/BV signature-plot flatness statistic once the Layer-1 methodology
    exists (see docs/IMPLEMENTATION_STATUS.md).
    """
    df = _simulate(n_minutes=5000, seed=0)
    returns = df["50Y"].diff().dropna()
    rho = returns.autocorr(lag=1)
    assert rho > -0.1, f"Expected non-negative autocorrelation; got rho={rho:.4f}"
