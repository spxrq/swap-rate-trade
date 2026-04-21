"""Random-walk efficient price plus iid Gaussian microstructure noise.

Adversarial / null DGP for the mean-reversion thesis. The efficient price is
a driftless random walk (unit root), so any mean-reversion detector that
succeeds on this data is producing a false positive.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def simulate(
    *,
    start_level: float,
    sigma_eff: float,
    sigma_noise: float,
    n_minutes: int,
    start: pd.Timestamp,
    seed: int | None = None,
    column_name: str = "50Y",
) -> pd.DataFrame:
    """Simulate a random-walk efficient price plus iid Gaussian noise.

    Parameters
    ----------
    start_level
        Level of the efficient price at ``t = 0``, in decimal form.
    sigma_eff
        Standard deviation of the per-minute efficient-price increments
        (level units).
    sigma_noise
        Standard deviation of the iid microstructure noise (level units).
    n_minutes
        Number of 1-minute observations to simulate.
    start
        Timestamp of the first observation. Should be timezone-aware (CET).
    seed
        RNG seed.
    column_name
        Column label in the returned DataFrame.

    Returns
    -------
    pd.DataFrame
        Single-column DataFrame with a 1-minute ``DatetimeIndex`` starting at
        ``start``. Values are observed rate levels (efficient + noise).
    """
    if start.tz is None:
        raise ValueError(
            f"`start` must be timezone-aware per docs/DATA_CONTRACT.md; "
            f"got naive timestamp {start!r}"
        )

    rng = np.random.default_rng(seed)
    increments = rng.normal(0.0, sigma_eff, size=n_minutes - 1)
    eff = np.empty(n_minutes, dtype=np.float64)
    eff[0] = start_level
    eff[1:] = start_level + np.cumsum(increments)

    noise = rng.normal(0.0, sigma_noise, size=n_minutes)
    observed = eff + noise

    idx = pd.date_range(start=start, periods=n_minutes, freq="1min")
    return pd.DataFrame({column_name: observed}, index=idx)
