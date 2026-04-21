"""Ornstein-Uhlenbeck efficient price plus iid Gaussian microstructure noise.

Thesis-matching DGP: the efficient rate mean-reverts around a constant level
`mu` at speed `theta` (half-life = ln(2) / theta minutes). The observed rate
is the efficient rate plus iid Gaussian noise, so at fine sampling Δ the
realized variance is inflated by the noise, and as Δ coarsens the noise
contribution to RV shrinks relative to the integrated variance of the efficient
price.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def simulate(
    *,
    mu: float,
    theta: float,
    sigma_eff: float,
    sigma_noise: float,
    n_minutes: int,
    start: pd.Timestamp,
    seed: int | None = None,
    column_name: str = "50Y",
) -> pd.DataFrame:
    """Simulate an OU efficient price plus iid Gaussian microstructure noise.

    Parameters
    ----------
    mu
        Long-run mean level the efficient price reverts to, in decimal form
        (e.g. ``0.045`` for 4.5%).
    theta
        Mean-reversion speed, per minute. Half-life = ``ln(2) / theta`` minutes.
    sigma_eff
        Instantaneous volatility of the efficient price (level units per
        sqrt(minute)).
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
    rng = np.random.default_rng(seed)

    # Exact discretization of dX = -theta (X - mu) dt + sigma_eff dW at dt=1:
    #   X_{t+1} = mu + (X_t - mu) * phi + cond_sd * Z,  Z ~ N(0, 1)
    phi = np.exp(-theta)
    cond_sd = sigma_eff * np.sqrt((1.0 - np.exp(-2.0 * theta)) / (2.0 * theta))

    eff = np.empty(n_minutes, dtype=np.float64)
    eff[0] = mu
    z = rng.standard_normal(n_minutes - 1)
    for i in range(1, n_minutes):
        eff[i] = mu + (eff[i - 1] - mu) * phi + cond_sd * z[i - 1]

    noise = rng.normal(0.0, sigma_noise, size=n_minutes)
    observed = eff + noise

    idx = pd.date_range(start=start, periods=n_minutes, freq="1min")
    return pd.DataFrame({column_name: observed}, index=idx)
