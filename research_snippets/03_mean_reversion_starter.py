# %%
# CELL 1 - imports
# Run this after setting EXCEL_PATH, after the Excel research starter, or after
# creating a 5m DataFrame named df_5. The script uses statsmodels for
# standardized time-series tests.
import re

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import statsmodels.api as sm
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
from statsmodels.stats.diagnostic import (
    acorr_breusch_godfrey,
    acorr_ljungbox,
    het_arch,
    het_breuschpagan,
)
from statsmodels.tsa.ar_model import AutoReg, ar_select_order
from statsmodels.tsa.stattools import adfuller, kpss

try:
    from arch import arch_model

    ARCH_AVAILABLE = True
except ImportError:
    arch_model = None
    ARCH_AVAILABLE = False


# %%
# CELL 2 - user config and research conventions
# Mean-reversion analysis should run on the selected clean sampling interval.
# Current working choice: 5 minutes.
#
# Rate change definition:
# - first level difference of the rate, converted to basis points
# - rate_change_bp[t] = 10000 * (rate_level[t] - rate_level[t-1])
# - not log change; swap rates can be near zero/negative, and PnL is linear in bp

MEAN_REVERSION_DELTA_MIN = globals().get("MEAN_REVERSION_DELTA_MIN", 5)
EXCEL_PATH = globals().get("EXCEL_PATH", None)
SHEET_PREFIX = globals().get("SHEET_PREFIX", "timestamp")
LOCAL_TZ = globals().get("LOCAL_TZ", "Europe/Amsterdam")
RATE_COL = globals().get("RATE_COL", None)
PREFERRED_RATE_COLS = ["50Y", "30Y", "20Y", "10Y", "PX_LAST", "LAST_PRICE", "VALUE"]
TIMESTAMP_COLS = ["timestamp", "datetime", "date_time", "time", "date"]
SESSION_START = globals().get("SESSION_START", "08:00")
SESSION_END = globals().get("SESSION_END", "17:00")
MAX_ACF_LAG = globals().get("MAX_ACF_LAG", 40)
LJUNG_BOX_LAGS = [5, 10, 20]
AR_MAX_LAGS = globals().get("AR_MAX_LAGS", 12)
ROLLING_WINDOW_BARS = globals().get("ROLLING_WINDOW_BARS", 24)
RATE_CHANGE_DEFINITION = "first level difference in bp: 10000 * rate.diff(); not log change"


# %%
# CELL 3 - input and validation helpers
# Input priority:
# 1. df_5 if MEAN_REVERSION_DELTA_MIN is 5
# 2. dfs_by_delta[5] if the Excel starter was run
# 3. EXCEL_PATH sheet timestamp5
# 4. df if a single 5m DataFrame was created manually
def _clean_col(col):
    return str(col).strip()


def _find_timestamp_col(df):
    lower_map = {_clean_col(col).lower(): col for col in df.columns}
    for name in TIMESTAMP_COLS:
        if name in lower_map:
            return lower_map[name]

    best_col = None
    best_valid = 0.0
    for col in df.columns[:4]:
        parsed = pd.to_datetime(df[col], errors="coerce")
        valid = float(parsed.notna().mean())
        if valid > best_valid:
            best_col = col
            best_valid = valid

    if best_col is None or best_valid < 0.80:
        raise ValueError("could not find a timestamp column")
    return best_col


def _localize_or_convert_index(index):
    if index.tz is None:
        try:
            return index.tz_localize(
                LOCAL_TZ,
                ambiguous="infer",
                nonexistent="shift_forward",
            )
        except Exception:
            return index.tz_localize(
                LOCAL_TZ,
                ambiguous="NaT",
                nonexistent="shift_forward",
            )
    return index.tz_convert(LOCAL_TZ)


def normalize_excel_sheet(raw):
    out = raw.copy()
    out.columns = [_clean_col(col) for col in out.columns]

    timestamp_col = _find_timestamp_col(out)
    timestamp = pd.to_datetime(out[timestamp_col], errors="coerce")
    out = out.loc[timestamp.notna()].copy()
    out.index = pd.DatetimeIndex(timestamp.loc[timestamp.notna()])
    out = out.drop(columns=[timestamp_col])

    out.index = _localize_or_convert_index(out.index)
    out = out.loc[~out.index.isna()]
    out = out.sort_index()
    out = out[~out.index.duplicated(keep="last")]

    for col in out.columns:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    return out.dropna(axis=1, how="all")


def load_delta_sheet_from_excel(excel_path, delta_min):
    xls = pd.ExcelFile(excel_path)
    pattern = re.compile(rf"^{re.escape(SHEET_PREFIX)}[_\s-]*{delta_min}$", re.IGNORECASE)
    matching = [sheet for sheet in xls.sheet_names if pattern.match(str(sheet).strip())]
    if not matching:
        raise ValueError(
            f"No sheet found for {SHEET_PREFIX}{delta_min}. "
            f"Available sheets: {xls.sheet_names}"
        )
    return normalize_excel_sheet(pd.read_excel(xls, sheet_name=matching[0])), matching[0]


def choose_rate_col(df):
    if RATE_COL is not None:
        if RATE_COL not in df.columns:
            raise ValueError(f"RATE_COL={RATE_COL} not found in input DataFrame")
        return RATE_COL

    for col in PREFERRED_RATE_COLS:
        if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
            return col

    numeric_cols = [col for col in df.columns if pd.api.types.is_numeric_dtype(df[col])]
    if len(numeric_cols) == 1:
        return numeric_cols[0]
    if not numeric_cols:
        raise ValueError("No numeric rate column found")
    raise ValueError(f"Multiple numeric columns found; set RATE_COL manually: {numeric_cols}")


def resolve_input_frame(delta_min):
    frame_name = f"df_{delta_min}"
    if frame_name in globals():
        return globals()[frame_name].copy(), frame_name

    if "dfs_by_delta" in globals() and delta_min in globals()["dfs_by_delta"]:
        return globals()["dfs_by_delta"][delta_min].copy(), f"dfs_by_delta[{delta_min}]"

    if EXCEL_PATH is not None:
        frame, sheet_name = load_delta_sheet_from_excel(EXCEL_PATH, delta_min)
        globals()[frame_name] = frame
        return frame.copy(), f"EXCEL_PATH[{sheet_name}]"

    if "df" in globals():
        return globals()["df"].copy(), "df"

    raise ValueError(
        f"Create df_{delta_min}, dfs_by_delta[{delta_min}], set EXCEL_PATH, or create df before running"
    )


def validate_frame(df):
    if not isinstance(df, pd.DataFrame):
        raise ValueError("input must be a pandas DataFrame")
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("input index must be a DatetimeIndex")

    out = df.sort_index()
    if out.index.has_duplicates:
        out = out[~out.index.duplicated(keep="last")]
    return out


def session_frame(df):
    return df.between_time(SESSION_START, SESSION_END, inclusive="left")


# %%
# CELL 4 - construct level, change, and squared-change series
# We inspect three objects:
# - level_bp: rate level in basis points
# - change_bp: 5m first difference in basis points
# - change_sq: squared 5m first difference, a volatility-clustering screen
raw_df, input_source = resolve_input_frame(MEAN_REVERSION_DELTA_MIN)
input_df = session_frame(validate_frame(raw_df))
RATE_COL = choose_rate_col(input_df)

level_bp = (1e4 * input_df[RATE_COL].astype(float)).dropna()
change_bp = level_bp.diff().dropna()
change_sq = change_bp.pow(2).dropna()

analysis_df = pd.DataFrame(
    {
        "level_bp": level_bp,
        "change_bp": change_bp,
        "change_sq": change_sq,
    }
).dropna()

if len(analysis_df) < 20:
    raise ValueError("Not enough 5m observations for mean-reversion diagnostics")


# %%
# CELL 5 - descriptive summary
# This table gives scale and distribution context before fitting any model.
summary_stats = pd.DataFrame(
    {
        "level_bp": analysis_df["level_bp"].describe(),
        "change_bp": analysis_df["change_bp"].describe(),
        "change_sq": analysis_df["change_sq"].describe(),
    }
)

session_counts = input_df.groupby(input_df.index.date).size()
daily_change_stats = analysis_df["change_bp"].groupby(analysis_df.index.date).agg(
    ["count", "mean", "std", "min", "max"]
)


# %%
# CELL 6 - ACF/PACF diagnostics
# Interpretation:
# - level ACF that decays slowly is normal for rates and does not by itself
#   prove exploitable mean reversion.
# - negative low-lag change ACF is the direct screen for short-horizon reversal.
# - squared-change ACF/PACF checks volatility clustering, not directional edge.
fig, axes = plt.subplots(3, 2, figsize=(13, 10))
series_map = [
    ("level_bp", "Level ACF/PACF"),
    ("change_bp", "5m Change ACF/PACF"),
    ("change_sq", "Squared 5m Change ACF/PACF"),
]

for row, (series_name, title) in enumerate(series_map):
    values = analysis_df[series_name].dropna()
    effective_lag = min(MAX_ACF_LAG, max(1, len(values) // 2 - 1))

    plot_acf(values, lags=effective_lag, alpha=0.05, zero=False, ax=axes[row, 0])
    axes[row, 0].set_title(f"{title}: ACF")
    axes[row, 0].set_xlabel("Lag")

    plot_pacf(values, lags=effective_lag, alpha=0.05, zero=False, method="ywm", ax=axes[row, 1])
    axes[row, 1].set_title(f"{title}: PACF")
    axes[row, 1].set_xlabel("Lag")

plt.tight_layout()
plt.show()


# %%
# CELL 7 - visual path diagnostics
# These plots help separate a statistical signal from obvious regime shifts.
fig, axes = plt.subplots(3, 1, figsize=(13, 9), sharex=True)

axes[0].plot(analysis_df.index, analysis_df["level_bp"], linewidth=1)
axes[0].set_title(f"{MEAN_REVERSION_DELTA_MIN}m rate level")
axes[0].set_ylabel("bp")
axes[0].grid(True, alpha=0.3)

axes[1].plot(analysis_df.index, analysis_df["change_bp"], linewidth=1)
axes[1].axhline(0.0, color="black", linewidth=1)
axes[1].set_title(f"{MEAN_REVERSION_DELTA_MIN}m rate change")
axes[1].set_ylabel("bp")
axes[1].grid(True, alpha=0.3)

rolling_vol = analysis_df["change_bp"].rolling(ROLLING_WINDOW_BARS).std()
axes[2].plot(rolling_vol.index, rolling_vol, linewidth=1)
axes[2].set_title(f"Rolling {ROLLING_WINDOW_BARS}-bar change volatility")
axes[2].set_ylabel("bp")
axes[2].grid(True, alpha=0.3)

plt.tight_layout()
plt.show()


# %%
# CELL 8 - AR(1) level mean-reversion estimate
# Model: level_t = alpha + phi * level_{t-1} + error_t.
# A phi below 1 suggests mean reversion; half-life is only meaningful for
# 0 < phi < 1 and should be treated cautiously when phi is very close to 1.
# This cell also fits a statsmodels AutoReg process selected by AIC as a
# higher-order AR benchmark for the next stage of the research.
# Half-life handling:
# - AR(1): half-life bars = log(0.5) / log(phi).
# - AR(p): use the companion matrix. The dominant root gives the smooth
#   persistence approximation; the impulse-response half-life gives the first
#   horizon where a unit shock has decayed below 50%.
ar1_data = pd.DataFrame(
    {
        "y": analysis_df["level_bp"],
        "lag1": analysis_df["level_bp"].shift(1),
    }
).dropna()

x = sm.add_constant(ar1_data["lag1"])
ar1_model = sm.OLS(ar1_data["y"], x).fit(cov_type="HAC", cov_kwds={"maxlags": 5})
phi = float(ar1_model.params["lag1"])
alpha = float(ar1_model.params["const"])
phi_t = float(ar1_model.tvalues["lag1"])
phi_p = float(ar1_model.pvalues["lag1"])
long_run_mean_bp = alpha / (1.0 - phi) if abs(1.0 - phi) > 1e-8 else np.nan
half_life_bars = -np.log(2.0) / np.log(phi) if 0.0 < phi < 1.0 else np.nan
half_life_minutes = half_life_bars * MEAN_REVERSION_DELTA_MIN if pd.notna(half_life_bars) else np.nan

ar1_summary = pd.DataFrame(
    {
        "value": {
            "alpha": alpha,
            "phi": phi,
            "phi_t_hac": phi_t,
            "phi_p_hac": phi_p,
            "long_run_mean_bp": long_run_mean_bp,
            "half_life_bars": half_life_bars,
            "half_life_minutes": half_life_minutes,
            "r_squared": float(ar1_model.rsquared),
        }
    }
)

selected_ar = ar_select_order(
    analysis_df["level_bp"],
    maxlag=min(AR_MAX_LAGS, max(1, len(analysis_df) // 5)),
    ic="aic",
    old_names=False,
)
selected_ar_lags = selected_ar.ar_lags if selected_ar.ar_lags else [1]
autoreg_model = AutoReg(
    analysis_df["level_bp"],
    lags=selected_ar_lags,
    old_names=False,
).fit()


def extract_autoreg_phi(model):
    lags = list(model.model.ar_lags)
    params = model.params
    phi = np.zeros(max(lags))
    for lag in lags:
        matches = [
            name for name in params.index
            if str(name).endswith(f".L{lag}") or str(name).endswith(f"L{lag}")
        ]
        if matches:
            phi[lag - 1] = float(params[matches[-1]])
    if np.allclose(phi, 0.0) and len(params) >= len(lags):
        for lag, value in zip(lags, params.iloc[-len(lags):]):
            phi[lag - 1] = float(value)
    return phi


def ar_half_life_from_phi(phi, max_horizon=500):
    phi = np.asarray(phi, dtype=float)
    phi = phi[np.isfinite(phi)]
    if len(phi) == 0:
        return {
            "dominant_root": np.nan,
            "stable": False,
            "half_life_bars_dominant_root": np.nan,
            "half_life_minutes_dominant_root": np.nan,
            "half_life_bars_irf": np.nan,
            "half_life_minutes_irf": np.nan,
        }

    p = len(phi)
    companion = np.zeros((p, p))
    companion[0, :] = phi
    if p > 1:
        companion[1:, :-1] = np.eye(p - 1)

    dominant_root = float(np.max(np.abs(np.linalg.eigvals(companion))))
    stable = bool(dominant_root < 1.0)
    root_half_life = (
        np.log(0.5) / np.log(dominant_root)
        if 0.0 < dominant_root < 1.0
        else np.nan
    )

    state = np.zeros(p)
    state[0] = 1.0
    irf_half_life = np.nan
    for horizon in range(1, max_horizon + 1):
        state = companion @ state
        if abs(state[0]) <= 0.5:
            irf_half_life = float(horizon)
            break

    return {
        "dominant_root": dominant_root,
        "stable": stable,
        "half_life_bars_dominant_root": float(root_half_life) if pd.notna(root_half_life) else np.nan,
        "half_life_minutes_dominant_root": (
            float(root_half_life * MEAN_REVERSION_DELTA_MIN)
            if pd.notna(root_half_life)
            else np.nan
        ),
        "half_life_bars_irf": irf_half_life,
        "half_life_minutes_irf": (
            float(irf_half_life * MEAN_REVERSION_DELTA_MIN)
            if pd.notna(irf_half_life)
            else np.nan
        ),
    }


autoreg_phi = extract_autoreg_phi(autoreg_model)
autoreg_half_life = ar_half_life_from_phi(autoreg_phi)

autoreg_summary = pd.DataFrame(
    {
        "value": {
            "selected_lags": str(selected_ar_lags),
            "phi_by_lag": str({i + 1: round(float(v), 6) for i, v in enumerate(autoreg_phi) if v != 0.0}),
            "aic": float(autoreg_model.aic),
            "bic": float(autoreg_model.bic),
            "hqic": float(autoreg_model.hqic),
            "nobs": int(autoreg_model.nobs),
            "dominant_root": autoreg_half_life["dominant_root"],
            "stable": autoreg_half_life["stable"],
            "half_life_bars_dominant_root": autoreg_half_life["half_life_bars_dominant_root"],
            "half_life_minutes_dominant_root": autoreg_half_life["half_life_minutes_dominant_root"],
            "half_life_bars_irf": autoreg_half_life["half_life_bars_irf"],
            "half_life_minutes_irf": autoreg_half_life["half_life_minutes_irf"],
        }
    }
)


# %%
# CELL 9 - stationarity, autocorrelation, and heteroskedasticity tests
# ADF null: level has a unit root.
# KPSS null: level is stationary around a constant.
# Ljung-Box: autocorrelation in changes and squared changes.
# Breusch-Godfrey LM: serial correlation in AR(1) residuals.
# Breusch-Pagan LM: heteroskedasticity linked to AR(1) regressors.
# ARCH LM: autoregressive conditional heteroskedasticity in AR(1) residuals.
adf_stat, adf_p, adf_lags, adf_nobs, adf_crit, _ = adfuller(
    analysis_df["level_bp"],
    autolag="AIC",
    regression="c",
)

try:
    kpss_stat, kpss_p, kpss_lags, kpss_crit = kpss(
        analysis_df["level_bp"],
        regression="c",
        nlags="auto",
    )
except Exception as exc:
    kpss_stat, kpss_p, kpss_lags, kpss_crit = np.nan, np.nan, np.nan, {}
    kpss_error = str(exc)
else:
    kpss_error = ""

stationarity_summary = pd.DataFrame(
    {
        "value": {
            "adf_stat": float(adf_stat),
            "adf_pvalue": float(adf_p),
            "adf_used_lags": int(adf_lags),
            "adf_nobs": int(adf_nobs),
            "adf_crit_1pct": float(adf_crit["1%"]),
            "adf_crit_5pct": float(adf_crit["5%"]),
            "adf_crit_10pct": float(adf_crit["10%"]),
            "kpss_stat": float(kpss_stat) if pd.notna(kpss_stat) else np.nan,
            "kpss_pvalue": float(kpss_p) if pd.notna(kpss_p) else np.nan,
            "kpss_used_lags": int(kpss_lags) if pd.notna(kpss_lags) else np.nan,
            "kpss_crit_1pct": float(kpss_crit.get("1%", np.nan)),
            "kpss_crit_5pct": float(kpss_crit.get("5%", np.nan)),
            "kpss_crit_10pct": float(kpss_crit.get("10%", np.nan)),
            "kpss_error": kpss_error,
        }
    }
)

lb_change = acorr_ljungbox(
    analysis_df["change_bp"],
    lags=LJUNG_BOX_LAGS,
    return_df=True,
).rename(columns={"lb_stat": "change_lb_stat", "lb_pvalue": "change_lb_pvalue"})

lb_sq = acorr_ljungbox(
    analysis_df["change_sq"],
    lags=LJUNG_BOX_LAGS,
    return_df=True,
).rename(columns={"lb_stat": "sq_change_lb_stat", "lb_pvalue": "sq_change_lb_pvalue"})

ljung_box_summary = pd.concat([lb_change, lb_sq], axis=1)

bg_lm, bg_lm_p, bg_f, bg_f_p = acorr_breusch_godfrey(ar1_model, nlags=5)
bp_lm, bp_lm_p, bp_f, bp_f_p = het_breuschpagan(ar1_model.resid, x)
arch_lm, arch_lm_p, arch_f, arch_f_p = het_arch(ar1_model.resid, nlags=10)

residual_diagnostics = pd.DataFrame(
    {
        "value": {
            "breusch_godfrey_lm_stat": float(bg_lm),
            "breusch_godfrey_lm_pvalue": float(bg_lm_p),
            "breusch_godfrey_f_stat": float(bg_f),
            "breusch_godfrey_f_pvalue": float(bg_f_p),
            "breusch_pagan_lm_stat": float(bp_lm),
            "breusch_pagan_lm_pvalue": float(bp_lm_p),
            "breusch_pagan_f_stat": float(bp_f),
            "breusch_pagan_f_pvalue": float(bp_f_p),
            "arch_lm_stat": float(arch_lm),
            "arch_lm_pvalue": float(arch_lm_p),
            "arch_f_stat": float(arch_f),
            "arch_f_pvalue": float(arch_f_p),
            "arch_library_available": bool(ARCH_AVAILABLE),
        }
    }
)


# %%
# CELL 10 - compact research readout
# Keeps output focused on diagnostics rather than raw timestamped rows.
def show_table(obj):
    if "display" in globals():
        display(obj)
    else:
        print(obj)


lag1_change_acf = float(analysis_df["change_bp"].autocorr(lag=1))
lag1_sq_acf = float(analysis_df["change_sq"].autocorr(lag=1))

print("MEAN_REVERSION_STARTER: pass")
print(f"INPUT_SOURCE: {input_source}")
print(f"RATE_COL: {RATE_COL}")
print(f"DELTA_MIN: {MEAN_REVERSION_DELTA_MIN}")
print(f"RATE_CHANGE_DEFINITION: {RATE_CHANGE_DEFINITION}")
print(f"N_OBS: {len(analysis_df)}")
print(f"SESSION_DAYS: {len(session_counts)}")
print(f"SESSION_BARS_MIN_MEDIAN_MAX: {session_counts.min()}/{session_counts.median():.1f}/{session_counts.max()}")
print(f"CHANGE_ACF_LAG1: {lag1_change_acf:.4f}")
print(f"SQ_CHANGE_ACF_LAG1: {lag1_sq_acf:.4f}")
print(f"AR1_PHI: {phi:.6f}")
print(f"AR1_HALF_LIFE_MIN: {half_life_minutes:.2f}" if pd.notna(half_life_minutes) else "AR1_HALF_LIFE_MIN: undefined")
print(f"AUTOREG_SELECTED_LAGS: {selected_ar_lags}")
print(f"AUTOREG_DOMINANT_ROOT: {autoreg_half_life['dominant_root']:.6f}")
print(
    f"AUTOREG_HALF_LIFE_MIN_DOMINANT_ROOT: {autoreg_half_life['half_life_minutes_dominant_root']:.2f}"
    if pd.notna(autoreg_half_life["half_life_minutes_dominant_root"])
    else "AUTOREG_HALF_LIFE_MIN_DOMINANT_ROOT: undefined"
)
print(f"ADF_PVALUE_LEVEL: {adf_p:.4f}")
print(f"KPSS_PVALUE_LEVEL: {kpss_p:.4f}" if pd.notna(kpss_p) else "KPSS_PVALUE_LEVEL: unavailable")
print(f"BREUSCH_GODFREY_PVALUE_AR1_RESID: {bg_lm_p:.4f}")
print(f"BREUSCH_PAGAN_PVALUE_AR1_RESID: {bp_lm_p:.4f}")
print(f"ARCH_LM_PVALUE_AR1_RESID: {arch_lm_p:.4f}")
print(f"ARCH_LIBRARY_AVAILABLE: {ARCH_AVAILABLE}")
print("INTERPRETATION_GUIDE: lower phi and lower ADF p-value support level mean reversion; high KPSS p-value supports stationarity; negative change ACF supports short-horizon reversal.")

print("\nSUMMARY_STATS")
show_table(summary_stats)

print("\nAR1_LEVEL_SUMMARY")
show_table(ar1_summary)

print("\nAUTOREG_LEVEL_SUMMARY")
show_table(autoreg_summary)

print("\nSTATIONARITY_SUMMARY")
show_table(stationarity_summary)

print("\nLJUNG_BOX_SUMMARY")
show_table(ljung_box_summary)

print("\nRESIDUAL_DIAGNOSTICS")
show_table(residual_diagnostics)
