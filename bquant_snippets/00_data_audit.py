import numpy as np
import pandas as pd


# BQUANT INPUT CELL
# In bQuant, create `df` first. Then paste/run this file.
#
# Expected minimal shape:
# - DatetimeIndex, timezone-aware if possible
# - one or more numeric rate-level columns in decimal form
# - intraday observations

PREFERRED_RATE_COLS = ["50Y", "30Y", "20Y", "10Y"]
SESSION_START = "08:00"
SESSION_END = "17:00"
EXPECTED_SESSION_MINUTES = 540


def choose_rate_col(df, preferred_cols=PREFERRED_RATE_COLS):
    for col in preferred_cols:
        if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
            return col

    numeric_cols = [col for col in df.columns if pd.api.types.is_numeric_dtype(df[col])]
    if len(numeric_cols) == 1:
        return numeric_cols[0]
    if not numeric_cols:
        raise ValueError("No numeric rate column found")
    raise ValueError(f"Multiple numeric columns found; set RATE_COL manually: {numeric_cols}")


def sorted_unique_index(df):
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("df index must be a DatetimeIndex")
    out = df.sort_index()
    if out.index.has_duplicates:
        out = out[~out.index.duplicated(keep="last")]
    return out


def infer_base_frequency_minutes(index):
    diffs = index.to_series().diff().dropna()
    if diffs.empty:
        return np.nan
    return diffs.dt.total_seconds().median() / 60.0


def session_slice(df, start=SESSION_START, end=SESSION_END):
    return df.between_time(start, end, inclusive="left")


def daily_session_counts(df):
    session_df = session_slice(df)
    if session_df.empty:
        return pd.Series(dtype="int64")
    return session_df.groupby(session_df.index.date).size()


def audit_df(df, rate_col=None):
    if not isinstance(df, pd.DataFrame):
        raise ValueError("df must be a pandas DataFrame")

    input_n_obs = int(len(df))
    input_monotonic = bool(df.index.is_monotonic_increasing) if isinstance(df.index, pd.DatetimeIndex) else False
    input_duplicates = int(df.index.duplicated().sum()) if isinstance(df.index, pd.DatetimeIndex) else 0

    df_clean = sorted_unique_index(df)
    rate_col = choose_rate_col(df_clean) if rate_col is None else rate_col
    if rate_col not in df_clean.columns:
        raise ValueError(f"RATE_COL not found: {rate_col}")
    if not pd.api.types.is_numeric_dtype(df_clean[rate_col]):
        raise ValueError(f"RATE_COL is not numeric: {rate_col}")

    base_freq_min = infer_base_frequency_minutes(df_clean.index)
    session_counts = daily_session_counts(df_clean)
    missing = int(df_clean[rate_col].isna().sum())

    complete_sessions = int((session_counts == EXPECTED_SESSION_MINUTES).sum())
    partial_sessions = int((session_counts != EXPECTED_SESSION_MINUTES).sum())

    audit = {
        "rate_col": rate_col,
        "n_obs": input_n_obs,
        "n_columns": int(len(df_clean.columns)),
        "tz_aware": bool(df_clean.index.tz is not None),
        "input_monotonic": input_monotonic,
        "input_duplicate_timestamps": input_duplicates,
        "n_obs_after_sort_dedup": int(len(df_clean)),
        "missing_values": missing,
        "median_frequency_min": float(base_freq_min) if pd.notna(base_freq_min) else np.nan,
        "session_days": int(len(session_counts)),
        "complete_sessions_540": complete_sessions,
        "partial_sessions": partial_sessions,
        "min_session_bars": int(session_counts.min()) if len(session_counts) else 0,
        "median_session_bars": float(session_counts.median()) if len(session_counts) else 0.0,
        "max_session_bars": int(session_counts.max()) if len(session_counts) else 0,
    }
    return df_clean, audit, session_counts


RATE_COL = globals().get("RATE_COL", None)
df, audit, session_counts = audit_df(df, RATE_COL)
RATE_COL = audit["rate_col"]

print("DATA_AUDIT: pass")
print(f"RATE_COL: {audit['rate_col']}")
print(f"N_OBS: {audit['n_obs']}")
print(f"N_COLUMNS: {audit['n_columns']}")
print(f"TZ_AWARE: {audit['tz_aware']}")
print(f"INPUT_MONOTONIC: {audit['input_monotonic']}")
print(f"INPUT_DUPLICATE_TIMESTAMPS: {audit['input_duplicate_timestamps']}")
print(f"N_OBS_AFTER_SORT_DEDUP: {audit['n_obs_after_sort_dedup']}")
print(f"MISSING_VALUES: {audit['missing_values']}")
print(f"MEDIAN_FREQUENCY_MIN: {audit['median_frequency_min']:.3f}")
print(f"SESSION_DAYS: {audit['session_days']}")
print(f"COMPLETE_SESSIONS_540: {audit['complete_sessions_540']}")
print(f"PARTIAL_SESSIONS: {audit['partial_sessions']}")
print(
    "SESSION_BARS_MIN_MEDIAN_MAX: "
    f"{audit['min_session_bars']}/"
    f"{audit['median_session_bars']:.1f}/"
    f"{audit['max_session_bars']}"
)

warnings = []
if not audit["tz_aware"]:
    warnings.append("index is timezone-naive; convert to CET before methodology notebooks")
if not audit["input_monotonic"]:
    warnings.append("input index was not monotonic; audit sorted a working copy")
if audit["input_duplicate_timestamps"] > 0:
    warnings.append("duplicate timestamps found; audit kept the last value in a working copy")
if audit["missing_values"] > 0:
    warnings.append("missing rate values; decide fill/drop rule before RV or OU estimation")
if abs(audit["median_frequency_min"] - 1.0) > 0.01:
    warnings.append("base frequency is not 1 minute; resampling/data request may need adjustment")
if audit["complete_sessions_540"] == 0:
    warnings.append("no complete 08:00-17:00 sessions with 540 bars")

if warnings:
    print("STAGE_STATUS: review")
    for warning in warnings:
        print(f"WARNING: {warning}")
else:
    print("STAGE_STATUS: pass")
