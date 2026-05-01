import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


PREFERRED_RATE_COLS = ["50Y", "30Y", "20Y", "10Y"]
RATE_COL = globals().get("RATE_COL", None)
DELTAS_MIN = [5, 15, 30, 60, 120]
WEDGE_TOL = 0.05
SESSION_MINUTES = 540


def choose_rate_col(df, preferred_cols=PREFERRED_RATE_COLS):
    if RATE_COL is not None:
        return RATE_COL
    for col in preferred_cols:
        if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
            return col
    numeric_cols = [col for col in df.columns if pd.api.types.is_numeric_dtype(df[col])]
    if len(numeric_cols) == 1:
        return numeric_cols[0]
    if not numeric_cols:
        raise ValueError("no numeric rate column found")
    raise ValueError(f"Multiple numeric columns found; set RATE_COL manually: {numeric_cols}")


def validate_input_df(df, rate_col=None):
    if not isinstance(df, pd.DataFrame):
        raise ValueError("df must be a pandas DataFrame")
    rate_col = choose_rate_col(df) if rate_col is None else rate_col
    if rate_col not in df.columns:
        raise ValueError(f"missing rate column: {rate_col}")
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("df index must be a DatetimeIndex")
    if df.index.tz is None:
        raise ValueError("df index must be timezone-aware")
    if not df.index.is_monotonic_increasing:
        raise ValueError("df index must be monotonic increasing")
    if df.index.has_duplicates:
        raise ValueError("df index has duplicate timestamps")
    if df[rate_col].isna().any():
        raise ValueError(f"{rate_col} contains missing values")
    if not pd.api.types.is_numeric_dtype(df[rate_col]):
        raise ValueError(f"{rate_col} must be numeric")
    return rate_col


def estimate_ou_params_1min(df, rate_col=RATE_COL):
    y = df[rate_col].astype(float).to_numpy()
    x = y[:-1]
    z = y[1:]
    x_mean = x.mean()
    z_mean = z.mean()
    denom = np.sum((x - x_mean) ** 2)
    if denom <= 0:
        raise ValueError("cannot estimate OU parameters from a constant series")

    phi = np.sum((x - x_mean) * (z - z_mean)) / denom
    phi = float(np.clip(phi, 1e-6, 0.999999))
    intercept = z_mean - phi * x_mean
    mu = intercept / (1.0 - phi)
    theta = -np.log(phi)

    resid = z - (intercept + phi * x)
    cond_var = np.var(resid, ddof=1)
    sigma_eff = np.sqrt(cond_var * 2.0 * theta / (1.0 - np.exp(-2.0 * theta)))
    return {"mu": mu, "theta": theta, "sigma_eff": sigma_eff, "phi": phi}


def rv_lagged_session(df, delta_min, rate_col=RATE_COL):
    returns = 1e4 * df[rate_col].diff(delta_min).dropna()
    return float((SESSION_MINUTES // delta_min) * np.mean(returns.to_numpy() ** 2))


def bv_lagged_session(df, delta_min, rate_col=RATE_COL):
    returns = np.abs(1e4 * df[rate_col].diff(delta_min).dropna().to_numpy())
    if len(returns) < 2:
        return np.nan
    scale = (SESSION_MINUTES // delta_min) / (len(returns) - 1)
    return float(scale * (np.pi / 2.0) * np.sum(returns[1:] * returns[:-1]))


def rv_ou_implied(delta_min, theta_per_min, sigma_eff, T=SESSION_MINUTES):
    n_delta = T // delta_min
    return (
        n_delta
        * 1e8
        * (sigma_eff**2 / theta_per_min)
        * (1.0 - np.exp(-theta_per_min * delta_min))
    )


RATE_COL = validate_input_df(df, RATE_COL)
ou = estimate_ou_params_1min(df, RATE_COL)

rv = pd.Series({delta: rv_lagged_session(df, delta, RATE_COL) for delta in DELTAS_MIN})
bv = pd.Series({delta: bv_lagged_session(df, delta, RATE_COL) for delta in DELTAS_MIN})
rv_ou = pd.Series(
    {
        delta: rv_ou_implied(delta, ou["theta"], ou["sigma_eff"])
        for delta in DELTAS_MIN
    }
)
n_delta = pd.Series({delta: SESSION_MINUTES // delta for delta in DELTAS_MIN})

diagnostics = pd.DataFrame(
    {
        "n_delta": n_delta,
        "rv": rv,
        "bv": bv,
        "rv_ou": rv_ou,
    }
)
diagnostics["rv_bv_ratio"] = diagnostics["rv"] / diagnostics["bv"]
diagnostics["ratio_to_ou"] = diagnostics["rv"] / diagnostics["rv_ou"]
diagnostics["wedge_frac"] = (diagnostics["rv"] - diagnostics["rv_ou"]) / diagnostics["rv_ou"]
diagnostics["sigma_hat_n_sq"] = (
    (diagnostics["rv"] - diagnostics["rv_ou"]) / (2.0 * diagnostics["n_delta"] * 1e8)
)

diagnostics["abs_wedge_frac"] = diagnostics["wedge_frac"].abs()
qualifying = diagnostics.index[diagnostics["abs_wedge_frac"] <= WEDGE_TOL]
delta_star = None if len(qualifying) == 0 else int(qualifying[0])
warnings = []
if (diagnostics["wedge_frac"] < -WEDGE_TOL).any():
    warnings.append("observed RV is materially below OU-implied RV at some deltas; review OU fit")

fig, axes = plt.subplots(1, 2, figsize=(12, 4))
x = np.array(DELTAS_MIN)

axes[0].plot(x, diagnostics.loc[DELTAS_MIN, "rv"], marker="o", label="Observed RV")
axes[0].plot(x, diagnostics.loc[DELTAS_MIN, "bv"], marker="s", linestyle="--", label="BV")
axes[0].plot(x, diagnostics.loc[DELTAS_MIN, "rv_ou"], color="black", linestyle="--", label="OU-implied RV")
axes[0].set_xscale("log")
axes[0].set_xticks(DELTAS_MIN)
axes[0].set_xticklabels([str(delta) for delta in DELTAS_MIN])
axes[0].set_xlabel("Sampling interval Δ (minutes)")
axes[0].set_ylabel("Session variation (bp²)")
axes[0].set_title("Raw variation")
axes[0].grid(True, which="both", alpha=0.3)
axes[0].legend()

axes[1].plot(x, diagnostics.loc[DELTAS_MIN, "ratio_to_ou"], marker="o", label="RV / OU-implied RV")
axes[1].axhline(1.0, color="black", linestyle="--", linewidth=1)
axes[1].set_xscale("log")
axes[1].set_xticks(DELTAS_MIN)
axes[1].set_xticklabels([str(delta) for delta in DELTAS_MIN])
axes[1].set_xlabel("Sampling interval Δ (minutes)")
axes[1].set_ylabel("Ratio")
axes[1].set_title("Noise-wedge diagnostic")
axes[1].grid(True, which="both", alpha=0.3)
axes[1].legend()

plt.tight_layout()
plt.show()

print("LAYER1_PATH: OU noise-wedge")
print(f"RATE_COL: {RATE_COL}")
print(f"DELTA_GRID: {DELTAS_MIN}")
print(f"OU_THETA_PER_MIN: {ou['theta']:.6g}")
print(f"OU_HALF_LIFE_MIN: {np.log(2.0) / ou['theta']:.2f}")
print(f"OU_SIGMA_EFF: {ou['sigma_eff']:.6g}")
print(f"WEDGE_TOL: {WEDGE_TOL:.3f}")
if delta_star is None:
    print("DELTA_STAR: ambiguous")
    warnings.append("no delta within wedge tolerance; widen grid or review OU/noise fit")
else:
    print(f"DELTA_STAR: {delta_star}")

small_delta = diagnostics.index <= 60
print(f"SIGMA_N_SQ_EST_SMALL_DELTA: {diagnostics.loc[small_delta, 'sigma_hat_n_sq'].mean():.4e}")
print("NOISE_WEDGE_BY_DELTA: " + ", ".join(
    f"{delta}m={diagnostics.loc[delta, 'wedge_frac']:.3f}" for delta in DELTAS_MIN
))
if warnings:
    for warning in warnings:
        print(f"WARNING: {warning}")
else:
    print("WARNINGS: none")

with pd.option_context("display.float_format", "{:.4e}".format):
    print(diagnostics)
