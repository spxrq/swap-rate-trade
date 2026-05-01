# %%
# CELL 1 - imports
# Paste this cell first. It loads the standard data, plotting, and time-series
# diagnostic libraries used by the rest of the notebook cells.
import re

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf


# %%
# CELL 2 - user config and research conventions
# Edit EXCEL_PATH before running. The remaining defaults are safe
# starting points for the timestamp5/timestamp60 workbook workflow.
#
# INPUT CELL
# Set EXCEL_PATH first, then run this file/cell.
#
# Example:
# EXCEL_PATH = r"C:\path\to\swap_data.xlsx"
#
# Expected sheet names:
# - timestamp5, timestamp15, timestamp30, timestamp60, timestamp120, ...
#
# This snippet creates:
# - dfs_by_delta: dict like {5: df_5, 60: df_60}
# - df_5, df_15, df_30, df_60, ... as separate DataFrames
# - returns_by_delta
# - distribution_summary
# - rv_bv_summary
# - candidate_delta
#
# Rate change definition:
# - first level difference of the rate, converted to basis points
# - rate_change_bp[t] = 10000 * (rate_level[t] - rate_level[t-1])
# - not log change; swap rates can be near zero/negative, and PnL is linear in bp

# Workbook location on the local machine.
EXCEL_PATH = globals().get("EXCEL_PATH", None)

# Sheet naming convention: timestamp5, timestamp15, timestamp60, etc.
SHEET_PREFIX = "timestamp"

# Session-local timezone. Amsterdam is CET/CEST and matches the current desk use.
LOCAL_TZ = globals().get("LOCAL_TZ", "Europe/Amsterdam")

# Set RATE_COL manually if the workbook has multiple numeric columns.
RATE_COL = globals().get("RATE_COL", None)
RATE_CHANGE_DEFINITION = "first level difference in bp: 10000 * rate.diff(); not log change"
PREFERRED_RATE_COLS = ["50Y", "30Y", "20Y", "10Y", "PX_LAST", "LAST_PRICE", "VALUE"]
TIMESTAMP_COLS = ["timestamp", "datetime", "date_time", "time", "date"]

# Intraday research window. Half-open: includes 08:00, excludes 17:00.
SESSION_START = "08:00"
SESSION_END = "17:00"

# ACF/PACF and granularity-screen settings.
MAX_ACF_LAG = 30
STABILITY_TOL = 0.10
RV_BV_RATIO_TOL = 0.10
MIN_DAILY_RETURNS = 4


if EXCEL_PATH is None:
    raise ValueError('Set EXCEL_PATH first, e.g. EXCEL_PATH = r"C:\\path\\to\\file.xlsx"')


# %%
# CELL 3 - workbook loading helpers
# These helpers normalize each timestamp sheet into a clean DataFrame with a
# timezone-aware DatetimeIndex and numeric rate columns.
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
    out = out.dropna(axis=1, how="all")
    return out


def load_timestamp_sheets(excel_path):
    """Load all sheets named timestamp<minutes> into {delta_min: DataFrame}."""
    xls = pd.ExcelFile(excel_path)
    pattern = re.compile(rf"^{re.escape(SHEET_PREFIX)}[_\s-]*(\d+)$", re.IGNORECASE)
    dfs = {}

    for sheet in xls.sheet_names:
        match = pattern.match(str(sheet).strip())
        if match is None:
            continue
        delta = int(match.group(1))
        dfs[delta] = normalize_excel_sheet(pd.read_excel(xls, sheet_name=sheet))

    if not dfs:
        raise ValueError(f"No sheets found matching {SHEET_PREFIX}<minutes>, e.g. timestamp5")

    return dict(sorted(dfs.items()))


# %%
# CELL 4 - research metric helpers
# Rate changes are always level differences in basis points. RV/BV is computed
# by day first, then averaged across days for each sampling interval.
def choose_rate_col(dfs):
    if RATE_COL is not None:
        missing = [delta for delta, frame in dfs.items() if RATE_COL not in frame.columns]
        if missing:
            raise ValueError(f"RATE_COL={RATE_COL} missing from deltas: {missing}")
        return RATE_COL

    first = next(iter(dfs.values()))
    for col in PREFERRED_RATE_COLS:
        if col in first.columns and pd.api.types.is_numeric_dtype(first[col]):
            return col

    numeric_cols = [col for col in first.columns if pd.api.types.is_numeric_dtype(first[col])]
    if not numeric_cols:
        raise ValueError("No numeric rate column found")

    coverage = first[numeric_cols].notna().mean().sort_values(ascending=False)
    return str(coverage.index[0])


def session_frame(df):
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("DataFrame index must be DatetimeIndex")
    return df.between_time(SESSION_START, SESSION_END, inclusive="left")


def returns_bp(df, rate_col):
    """First level difference in basis points, not log return."""
    x = session_frame(df)[rate_col].astype(float).dropna()
    return (1e4 * x.diff()).dropna()


def distribution_row(delta, r, df):
    grouped = session_frame(df).groupby(session_frame(df).index.date).size()
    return {
        "delta_min": delta,
        "n_obs": int(len(df)),
        "session_days": int(len(grouped)),
        "median_bars_day": float(grouped.median()) if len(grouped) else np.nan,
        "n_returns": int(len(r)),
        "mean_bp": float(r.mean()) if len(r) else np.nan,
        "std_bp": float(r.std(ddof=1)) if len(r) > 1 else np.nan,
        "skew": float(r.skew()) if len(r) > 2 else np.nan,
        "excess_kurt": float(r.kurt()) if len(r) > 3 else np.nan,
        "q01_bp": float(r.quantile(0.01)) if len(r) else np.nan,
        "q05_bp": float(r.quantile(0.05)) if len(r) else np.nan,
        "q50_bp": float(r.quantile(0.50)) if len(r) else np.nan,
        "q95_bp": float(r.quantile(0.95)) if len(r) else np.nan,
        "q99_bp": float(r.quantile(0.99)) if len(r) else np.nan,
    }


def rv_bv_for_one_day(values):
    """Daily realized variance and bipower variation from bp rate changes."""
    r = 1e4 * values.astype(float).dropna().diff().dropna().to_numpy()
    if len(r) == 0:
        return np.nan, np.nan, 0
    rv = float(np.sum(r**2))
    bv = np.nan if len(r) < 2 else float((np.pi / 2.0) * np.sum(np.abs(r[1:]) * np.abs(r[:-1])))
    return rv, bv, int(len(r))


def rv_bv_summary_for_delta(delta, df, rate_col):
    rows = []
    for day, day_frame in session_frame(df).groupby(session_frame(df).index.date):
        rv, bv, n_ret = rv_bv_for_one_day(day_frame[rate_col])
        rows.append({"day": day, "rv": rv, "bv": bv, "n_returns": n_ret})

    daily = pd.DataFrame(rows)
    if daily.empty:
        return {
            "delta_min": delta,
            "days": 0,
            "mean_daily_returns": np.nan,
            "rv_mean": np.nan,
            "rv_std": np.nan,
            "bv_mean": np.nan,
            "bv_std": np.nan,
            "rv_bv_ratio": np.nan,
        }

    rv_mean = daily["rv"].mean()
    bv_mean = daily["bv"].mean()
    return {
        "delta_min": delta,
        "days": int(len(daily)),
        "mean_daily_returns": float(daily["n_returns"].mean()),
        "rv_mean": float(rv_mean),
        "rv_std": float(daily["rv"].std(ddof=1)),
        "bv_mean": float(bv_mean),
        "bv_std": float(daily["bv"].std(ddof=1)),
        "rv_bv_ratio": float(rv_mean / bv_mean) if pd.notna(bv_mean) and bv_mean != 0 else np.nan,
    }


def select_candidate_delta(summary):
    """Simple screening rule; final granularity still needs econometric review."""
    table = summary.copy().sort_index()
    table["rv_norm_to_coarsest"] = table["rv_mean"] / table["rv_mean"].dropna().iloc[-1]
    table["rv_adjacent_change"] = table["rv_mean"].pct_change().abs()
    table["rv_bv_gap"] = (table["rv_bv_ratio"] - 1.0).abs()

    eligible = table[
        (table["mean_daily_returns"] >= MIN_DAILY_RETURNS)
        & (table["rv_adjacent_change"] <= STABILITY_TOL)
        & (table["rv_bv_gap"] <= RV_BV_RATIO_TOL)
    ]
    if eligible.empty:
        return None, table
    return int(eligible.index[0]), table


def show_table(obj):
    if "display" in globals():
        display(obj)
    else:
        print(obj)


# %%
# CELL 5 - load workbook and create separate DataFrames
# Output objects:
# - dfs_by_delta: dictionary keyed by sampling interval in minutes
# - df_5, df_15, df_30, df_60, ...: separate DataFrames for notebook work
# - returns_by_delta: first-difference bp rate changes for each interval
dfs_by_delta = load_timestamp_sheets(EXCEL_PATH)
for _delta, _df in dfs_by_delta.items():
    globals()[f"df_{_delta}"] = _df

RATE_COL = choose_rate_col(dfs_by_delta)
returns_by_delta = {
    delta: returns_bp(frame, RATE_COL)
    for delta, frame in dfs_by_delta.items()
}

distribution_summary = pd.DataFrame(
    [
        distribution_row(delta, returns_by_delta[delta], frame)
        for delta, frame in dfs_by_delta.items()
    ]
).set_index("delta_min")

rv_bv_summary = pd.DataFrame(
    [
        rv_bv_summary_for_delta(delta, frame, RATE_COL)
        for delta, frame in dfs_by_delta.items()
    ]
).set_index("delta_min")

candidate_delta, rv_bv_summary = select_candidate_delta(rv_bv_summary)


# %%
# CELL 6 - distribution, ACF, and PACF plots
# Plots the finest available interval and 60m when present. ACF/PACF come from
# statsmodels, so the confidence bands and estimators are standardized.
plot_deltas = [min(dfs_by_delta)]
if 60 in dfs_by_delta and 60 not in plot_deltas:
    plot_deltas.append(60)
elif max(dfs_by_delta) not in plot_deltas:
    plot_deltas.append(max(dfs_by_delta))

fig, axes = plt.subplots(len(plot_deltas), 3, figsize=(14, 3.6 * len(plot_deltas)))
if len(plot_deltas) == 1:
    axes = np.array([axes])

for row, delta in enumerate(plot_deltas):
    r = returns_by_delta[delta].dropna()
    effective_lag = min(MAX_ACF_LAG, max(1, len(r) // 2 - 1))

    axes[row, 0].hist(r, bins=60, density=True, alpha=0.75)
    axes[row, 0].axvline(0.0, color="black", linewidth=1)
    axes[row, 0].set_title(f"{delta}m return distribution")
    axes[row, 0].set_xlabel("Rate change (bp)")
    axes[row, 0].set_ylabel("Density")

    if len(r) >= 4:
        plot_acf(r, lags=effective_lag, alpha=0.05, zero=False, ax=axes[row, 1])
    else:
        axes[row, 1].text(0.5, 0.5, "not enough observations", ha="center", va="center")
    axes[row, 1].set_title(f"{delta}m return ACF")
    axes[row, 1].set_xlabel("Lag")

    if len(r) >= 4:
        plot_pacf(r, lags=effective_lag, alpha=0.05, zero=False, method="ywm", ax=axes[row, 2])
    else:
        axes[row, 2].text(0.5, 0.5, "not enough observations", ha="center", va="center")
    axes[row, 2].set_title(f"{delta}m return PACF")
    axes[row, 2].set_xlabel("Lag")

plt.tight_layout()
plt.show()


# %%
# CELL 7 - RV/BV granularity screen
# RV and BV are shown across all loaded timestamp sheets. Fine-grid RV inflation
# relative to coarser intervals is the first visual check for microstructure
# noise, but this is only a screen, not the final delta decision.
fig, axes = plt.subplots(1, 2, figsize=(12, 4))
x = rv_bv_summary.index.to_numpy()

axes[0].plot(x, rv_bv_summary["rv_mean"], marker="o", label="RV")
axes[0].plot(x, rv_bv_summary["bv_mean"], marker="s", linestyle="--", label="BV")
axes[0].set_xscale("log")
axes[0].set_xticks(x)
axes[0].set_xticklabels([str(int(v)) for v in x])
axes[0].set_xlabel("Sampling interval (minutes)")
axes[0].set_ylabel("Mean daily variation (bp^2)")
axes[0].set_title("RV/BV signature")
axes[0].grid(True, which="both", alpha=0.3)
axes[0].legend()

axes[1].plot(x, rv_bv_summary["rv_norm_to_coarsest"], marker="o", label="RV / coarsest RV")
axes[1].plot(x, rv_bv_summary["rv_bv_ratio"], marker="s", label="RV / BV")
axes[1].axhline(1.0, color="black", linestyle="--", linewidth=1)
axes[1].set_xscale("log")
axes[1].set_xticks(x)
axes[1].set_xticklabels([str(int(v)) for v in x])
axes[1].set_xlabel("Sampling interval (minutes)")
axes[1].set_title("Noise screen")
axes[1].grid(True, which="both", alpha=0.3)
axes[1].legend()

plt.tight_layout()
plt.show()


# %%
# CELL 8 - compact operator readout
# Safe to read out verbally: no raw timestamped rates or rows are printed.
print("EXCEL_RESEARCH_STARTER: pass")
print(f"RATE_COL: {RATE_COL}")
print(f"RATE_CHANGE_DEFINITION: {RATE_CHANGE_DEFINITION}")
print("LOADED_DELTAS: " + ", ".join(f"{delta}m" for delta in dfs_by_delta))
print("CREATED_FRAMES: " + ", ".join(f"df_{delta}" for delta in dfs_by_delta))
print(f"SESSION: {SESSION_START}-{SESSION_END} {LOCAL_TZ}")
print(f"ACF_PACF_PLOT_DELTAS: {plot_deltas}")
print(f"CANDIDATE_DELTA_HEURISTIC: {candidate_delta if candidate_delta is not None else 'review'}")
print("NOTE: heuristic candidate is a screen; confirm with the OU noise-wedge snippet if 1m data is available.")

print("\nDISTRIBUTION_SUMMARY")
show_table(distribution_summary)

print("\nRV_BV_SUMMARY")
show_table(rv_bv_summary)
