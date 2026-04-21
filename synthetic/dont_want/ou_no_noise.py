"""Pure Ornstein-Uhlenbeck efficient price with no microstructure noise.

Adversarial / null DGP for the microstructure-noise thesis. The observed
series equals the efficient price exactly, so a realized-variance signature
plot should be approximately flat across sampling frequencies. A Layer-1
detector that "finds" microstructure noise here is producing a false positive.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def simulate(
    *,
    mu: float,
    theta: float,
    sigma_eff: float,
    n_minutes: int,
    start: pd.Timestamp,
    seed: int | None = None,
    column_name: str = "50Y",
) -> pd.DataFrame:
    """Simulate an OU efficient price with no microstructure noise overlay.

    Parameters match :mod:`synthetic.want.ou_with_noise` minus ``sigma_noise``.

    Returns
    -------
    pd.DataFrame
        Single-column DataFrame with a 1-minute ``DatetimeIndex`` starting at
        ``start``. Values are the efficient rate level (no noise).
    """
    if start.tz is None:
        raise ValueError(
            f"`start` must be timezone-aware per docs/DATA_CONTRACT.md; "
            f"got naive timestamp {start!r}"
        )

    rng = np.random.default_rng(seed)

    phi = np.exp(-theta)
    cond_sd = sigma_eff * np.sqrt((1.0 - np.exp(-2.0 * theta)) / (2.0 * theta))

    eff = np.empty(n_minutes, dtype=np.float64)
    eff[0] = mu
    z = rng.standard_normal(n_minutes - 1)
    for i in range(1, n_minutes):
        eff[i] = mu + (eff[i - 1] - mu) * phi + cond_sd * z[i - 1]

    idx = pd.date_range(start=start, periods=n_minutes, freq="1min")
    return pd.DataFrame({column_name: eff}, index=idx)
