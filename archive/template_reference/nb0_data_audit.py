"""
================================================================================
NOTEBOOK 0: DATA AUDIT & INVENTORY
================================================================================
Purpose:
    Before any modeling, establish exactly what data is available.
    The outputs of this notebook determine which tracks are feasible
    and what model complexity is realistic.

Run this AT the Excel terminal. Fill in the findings as you go.
================================================================================
"""

import numpy as np
import pandas as pd
import os
from datetime import datetime

OUTPUT_DIR = './swap_research'
os.makedirs(OUTPUT_DIR, exist_ok=True)


# =============================================================================
# PART A: BLOOMBERG INTRADAY DATA AVAILABILITY
# =============================================================================
"""
For each ticker below, check on Excel:
    1. BTIC <GO> - what intraday bar sizes are available?
    2. How far back does intraday history go? (typically ~140 trading days)
    3. Are volume / number-of-trades fields populated for this ticker?
    4. Is this a composite mid (generic) or a specific source (Tradeweb/ICAP)?

Fill in the dictionary below as you explore.
"""

# -- Configure tickers to audit
TICKERS_TO_CHECK = [
    'EUSA10 Curncy',
    'EUSA15 Curncy',
    'EUSA20 Curncy',
    'EUSA25 Curncy',
    'EUSA30 Curncy',
    'EUSA40 Curncy',
    'EUSA50 Curncy',
    # Add Tradeweb / ICAP specific tickers if available:
    # 'EUSWI30 Curncy',
    # etc.
]

# -- Fill this in manually as you check each ticker
data_audit = {
    # 'EUSA30 Curncy': {
    #     'min_bar_size': 1,           # Smallest bar available (minutes)
    #     'history_start': '2025-10-01', # Earliest intraday date available
    #     'has_volume': True/False,
    #     'has_num_trades': True/False,
    #     'source_type': 'composite',  # 'composite', 'tradeweb', 'icap', etc.
    #     'notes': 'any quirks observed',
    # },
}

def print_audit_summary():
    """Print what we know so far."""
    if not data_audit:
        print("No audit data filled in yet. Check each ticker on Excel.")
        return

    df = pd.DataFrame(data_audit).T
    print("\nExcel Intraday Data Audit:")
    print(df.to_string())

    # Flag which tenors are viable for intraday analysis
    print("\nViability assessment:")
    for ticker, info in data_audit.items():
        tenor = ticker.replace('EUSA', '').replace(' Curncy', '') + 'Y'
        if info.get('min_bar_size', 999) <= 5:
            print(f"  {tenor}: HIGH resolution available ({info['min_bar_size']}min bars)")
        elif info.get('min_bar_size', 999) <= 15:
            print(f"  {tenor}: MODERATE resolution ({info['min_bar_size']}min bars)")
        else:
            print(f"  {tenor}: LOW resolution - intraday modeling may be limited")

        if not info.get('has_volume', False):
            print(f"         NOTE: No volume data - Track C liquidity conditioning limited")


# =============================================================================
# PART B: BLOOMBERG DATA PULL FUNCTIONS
# =============================================================================
"""
Two methods provided. Test both; use whichever works on your terminal.
"""

def pull_bbg_xbbg(ticker, date_str, interval=1):
    """Pull intraday bars for a single day using xbbg."""
    from xbbg import blp
    df = blp.bdib(
        ticker=ticker,
        dt=date_str,
        session='allday',
        typ='TRADE',
        interval=interval,
    )
    return df


def pull_bbg_blpapi(ticker, start_date, end_date, interval=1):
    """Pull intraday bars using raw blpapi."""
    import blpapi

    session_options = blpapi.SessionOptions()
    session_options.setServerHost('localhost')
    session_options.setServerPort(8194)
    session = blpapi.Session(session_options)

    if not session.start() or not session.openService('//blp/refdata'):
        raise ConnectionError("Cannot connect to Excel API")

    service = session.getService('//blp/refdata')
    request = service.createRequest('IntradayBarRequest')
    request.set('security', ticker)
    request.set('eventType', 'TRADE')
    request.set('interval', interval)
    request.set('startDateTime', f'{start_date}T07:00:00')
    request.set('endDateTime', f'{end_date}T18:00:00')

    session.sendRequest(request)

    rows = []
    while True:
        event = session.nextEvent(500)
        for msg in event:
            if msg.hasElement('barData'):
                bar_data = msg.getElement('barData').getElement('barTickData')
                for i in range(bar_data.numValues()):
                    bar = bar_data.getValueAsElement(i)
                    rows.append({
                        'time':   bar.getElementAsDatetime('time'),
                        'open':   bar.getElementAsFloat('open'),
                        'high':   bar.getElementAsFloat('high'),
                        'low':    bar.getElementAsFloat('low'),
                        'close':  bar.getElementAsFloat('close'),
                        'volume': bar.getElementAsInteger('volume'),
                        'n_trds': bar.getElementAsInteger('numEvents'),
                    })
        if event.eventType() == blpapi.Event.RESPONSE:
            break

    session.stop()
    return pd.DataFrame(rows).set_index('time')


def pull_full_history(ticker, start_date, end_date, interval=1, method='xbbg'):
    """
    Pull full intraday history for a ticker, day by day.
    Saves to parquet.
    """
    pull_fn = pull_bbg_xbbg if method == 'xbbg' else pull_bbg_blpapi
    date_range = pd.bdate_range(start_date, end_date)

    frames = []
    for dt in date_range:
        dt_str = dt.strftime('%Y-%m-%d')
        try:
            if method == 'xbbg':
                df = pull_fn(ticker, dt_str, interval=interval)
            else:
                df = pull_fn(ticker, dt_str, dt_str, interval=interval)
            if len(df) > 0:
                frames.append(df)
        except Exception as e:
            print(f"  Skip {dt_str}: {e}")

    if not frames:
        print(f"No data retrieved for {ticker}")
        return None

    combined = pd.concat(frames)
    safe_name = ticker.replace(' ', '_')
    path = f'{OUTPUT_DIR}/{safe_name}_{interval}min.parquet'
    combined.to_parquet(path)
    print(f"Saved {len(combined)} bars to {path}")
    return combined


def filter_trading_hours(df, start='07:30', end='17:30'):
    """Keep only core EUR swap trading hours (CET)."""
    sh, sm = map(int, start.split(':'))
    eh, em = map(int, end.split(':'))
    mask = (
        (df.index.hour > sh) | ((df.index.hour == sh) & (df.index.minute >= sm))
    ) & (
        (df.index.hour < eh) | ((df.index.hour == eh) & (df.index.minute <= em))
    )
    return df[mask]


# =============================================================================
# PART C: INTERNAL ORDER DATA INVENTORY
# =============================================================================
"""
After talking to your supervisor, fill in what the internal data looks like.
This determines Track B feasibility.
"""

internal_data_audit = {
    # 'source': 'trade booking system / Excel / ...',
    # 'fields_available': ['timestamp', 'notional', 'tenor', 'direction', ...],
    # 'timestamp_precision': 'minute / hour / day',
    # 'date_range': ('2024-01-01', '2026-04-01'),
    # 'can_distinguish_trade_type': True/False,  # issuance hedge vs other
    # 'approximate_n_issuance_hedges': 50,       # rough count
    # 'approximate_n_other_trades': 200,
    # 'notes': '',
}

def assess_track_b_feasibility():
    """Based on internal data audit, determine which Track B branch to take."""
    n = internal_data_audit.get('approximate_n_issuance_hedges', 0)
    precision = internal_data_audit.get('timestamp_precision', 'unknown')

    print("\nTrack B Feasibility Assessment:")
    print(f"  Issuance hedge events: ~{n}")
    print(f"  Timestamp precision: {precision}")

    if precision == 'day':
        print("\n  WARNING: Daily timestamps only.")
        print("  Cannot match to intraday bars from Track A.")
        print("  Track B limited to daily impact analysis only.")
        print("  -> Still useful, but cannot inform intraday execution timing.")
    elif precision in ('minute', 'second'):
        print(f"\n  Timestamp precision sufficient for intraday matching.")

    if n >= 50:
        print(f"\n  BRANCH: Large sample (n >= 50)")
        print("  -> Full OLS impulse response with HAC standard errors")
        print("  -> Can include controls and condition on subgroups")
        print("  -> Can test for asymmetry (buy vs sell impact)")
    elif n >= 15:
        print(f"\n  BRANCH: Medium sample (15 <= n < 50)")
        print("  -> OLS impulse response, but keep specification parsimonious")
        print("  -> Bootstrap confidence intervals instead of asymptotic")
        print("  -> No subgroup analysis (insufficient power)")
    elif n > 0:
        print(f"\n  BRANCH: Small sample (n < 15)")
        print("  -> Formal regression unreliable")
        print("  -> Descriptive event study: plot average rate path around events")
        print("  -> Report as suggestive evidence, not formal test")
    else:
        print(f"\n  No data available. Track B not feasible.")

    return n, precision


# =============================================================================
# PART D: QUICK DATA SANITY CHECK
# =============================================================================
"""
Once you've pulled data for at least one ticker, run these basic checks
before proceeding to Notebook 1.
"""

def sanity_check(df, ticker_name=""):
    """Basic data quality checks."""
    print(f"\n{'='*60}")
    print(f"Sanity Check: {ticker_name}")
    print(f"{'='*60}")

    print(f"\nShape: {df.shape}")
    print(f"Date range: {df.index.min()} to {df.index.max()}")
    print(f"Trading days: {df.index.normalize().nunique()}")

    # Bars per day
    bars_per_day = df.groupby(df.index.date).size()
    print(f"\nBars per day: mean={bars_per_day.mean():.0f}, "
          f"min={bars_per_day.min()}, max={bars_per_day.max()}")

    # Missing data
    print(f"\nNaN counts:")
    print(df.isnull().sum())

    # Price range
    print(f"\nClose price stats:")
    print(df['close'].describe())

    # Check for stale prices (consecutive identical closes)
    stale = (df['close'].diff() == 0).sum()
    stale_pct = stale / len(df) * 100
    print(f"\nStale prices (consecutive identical closes): "
          f"{stale} ({stale_pct:.1f}%)")
    if stale_pct > 30:
        print("  WARNING: High stale price percentage.")
        print("  This ticker may be too illiquid for intraday analysis,")
        print("  or the bar size may be too small. Try larger bars.")

    # Check for gaps
    time_diffs = df.index.to_series().diff()
    median_gap = time_diffs.median()
    large_gaps = time_diffs[time_diffs > 5 * median_gap].dropna()
    if len(large_gaps) > 0:
        print(f"\nLarge gaps detected (>{5*median_gap}):")
        for idx, gap in large_gaps.head(10).items():
            print(f"  {idx}: {gap}")

    # Volume check (if available)
    if 'volume' in df.columns:
        zero_vol = (df['volume'] == 0).sum()
        print(f"\nZero-volume bars: {zero_vol} ({zero_vol/len(df)*100:.1f}%)")
    else:
        print("\nNo volume column available.")

    return {
        'n_days': df.index.normalize().nunique(),
        'bars_per_day_mean': bars_per_day.mean(),
        'stale_pct': stale_pct,
        'has_volume': 'volume' in df.columns,
    }


# =============================================================================
# EXECUTION
# =============================================================================
"""
Workflow:
    1. Fill in data_audit dict as you check tickers on Excel
    2. Run print_audit_summary() to see what you have
    3. Pull data for the most promising ticker(s) using pull_full_history()
    4. Filter trading hours
    5. Run sanity_check() on the pulled data
    6. Fill in internal_data_audit after supervisor meeting
    7. Run assess_track_b_feasibility()

Once complete, you know:
    - Which tenors are viable for intraday analysis
    - Whether volume data is available (Track C feasibility)
    - What the internal order data looks like (Track B branch)

Then proceed to Notebook 1.
"""

# Example execution (uncomment on terminal):
#
# -- Step 1: Pull data for primary tenor
# df_30y = pull_full_history('EUSA30 Curncy', '2025-10-01', '2026-04-11',
#                            interval=1, method='xbbg')
#
# -- Step 2: Filter to trading hours
# df_30y = filter_trading_hours(df_30y)
#
# -- Step 3: Sanity check
# sanity_check(df_30y, 'EUSA30 1-min')
#
# -- Step 4: After supervisor meeting
# assess_track_b_feasibility()

print("Notebook 0 loaded. Start with the Excel data audit.")
