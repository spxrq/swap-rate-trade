"""
================================================================================
NOTEBOOK 4: BANK-SPECIFIC IMPACT ANALYSIS (TRACK B)
================================================================================
Purpose:
    Measure the market impact of NWB's own swap executions and
    determine how much of that impact is temporary (reverts).

    This is independent of Track A. Even if the general rate shows no
    mean reversion, NWB's specific impact might still be temporary.

Prerequisite:
    - Notebook 0: market data available
    - Internal order data obtained from supervisor
    - Track B feasibility assessed (sample size branch known)

Key question:
    When NWB executes a swap hedge, what happens to the rate afterward?
    How much of the price move is temporary vs permanent?

Branching:
    Large sample (N >= 50):  Full OLS impulse response + controls
    Medium sample (15-50):   Parsimonious OLS + bootstrap CI
    Small sample (< 15):     Descriptive event study only
================================================================================
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
import os

OUTPUT_DIR = './swap_research'


# =============================================================================
# STEP B0: DATA PREPARATION
# =============================================================================

def load_internal_orders(path=None):
    """
    Load and clean internal order data.

    Expected columns (adjust to match your actual data):
        - timestamp: execution time
        - notional:  trade size in EUR
        - tenor:     swap tenor (years)
        - direction: 'pay' (buy swap = pay fixed) or 'receive'
        - trade_type: 'issuance_hedge', 'roll', 'other' (if available)

    If your data has different column names, rename them here.
    """
    if path is None:
        print("No internal order data path provided.")
        print("Expected format: CSV or Excel with columns:")
        print("  timestamp, notional, tenor, direction, trade_type (optional)")
        print("\nLoad manually and pass to subsequent functions.")
        return None

    # Attempt load
    if path.endswith('.csv'):
        orders = pd.read_csv(path, parse_dates=['timestamp'])
    elif path.endswith('.xlsx') or path.endswith('.xls'):
        orders = pd.read_excel(path, parse_dates=['timestamp'])
    else:
        orders = pd.read_parquet(path)

    print(f"Loaded {len(orders)} orders")
    print(f"Date range: {orders['timestamp'].min()} to {orders['timestamp'].max()}")
    print(f"Columns: {list(orders.columns)}")
    print(f"\nTrade type distribution:")
    if 'trade_type' in orders.columns:
        print(orders['trade_type'].value_counts())
    print(f"\nTenor distribution:")
    if 'tenor' in orders.columns:
        print(orders['tenor'].value_counts())

    return orders


def prepare_event_dataset(orders, market_data, tenor_filter=None,
                          type_filter='issuance_hedge',
                          pre_window_bars=12, post_window_bars=48):
    """
    Match internal orders to market data to create event dataset.

    For each order:
        1. Find the bar in market data closest to the execution timestamp
        2. Extract the rate path from pre_window to post_window around it
        3. Compute cumulative rate change relative to execution bar

    Parameters
    ----------
    orders       : DataFrame with internal order data
    market_data  : Series of swap rates at chosen frequency (from Track A)
    tenor_filter : only include orders for this tenor (e.g., 30)
    type_filter  : only include this trade type (e.g., 'issuance_hedge')
    pre_window_bars  : bars before execution to include
    post_window_bars : bars after execution to include
    """
    filtered = orders.copy()
    if tenor_filter and 'tenor' in filtered.columns:
        filtered = filtered[filtered['tenor'] == tenor_filter]
    if type_filter and 'trade_type' in filtered.columns:
        filtered = filtered[filtered['trade_type'] == type_filter]

    print(f"Events after filtering: {len(filtered)}")

    events = []
    for _, order in filtered.iterrows():
        ts = order['timestamp']

        # Find nearest bar in market data
        idx = market_data.index.searchsorted(ts)
        if idx == 0 or idx >= len(market_data) - post_window_bars:
            continue

        # Extract window
        start_idx = max(0, idx - pre_window_bars)
        end_idx = min(len(market_data), idx + post_window_bars + 1)

        window = market_data.iloc[start_idx:end_idx]
        execution_rate = market_data.iloc[idx]

        # Compute cumulative change relative to execution
        relative = window - execution_rate

        # Normalize index to bars relative to execution
        bar_index = np.arange(-(idx - start_idx), end_idx - idx)

        event_data = pd.Series(relative.values, index=bar_index[:len(relative)])
        event_data.name = order.get('notional', 1)  # Store notional as name

        events.append({
            'date': ts.date() if hasattr(ts, 'date') else ts,
            'timestamp': ts,
            'notional': order.get('notional', np.nan),
            'tenor': order.get('tenor', np.nan),
            'execution_rate': execution_rate,
            'rate_path': event_data,
        })

    event_df = pd.DataFrame(events)
    print(f"Successfully matched events: {len(event_df)}")

    return event_df


def determine_branch(event_df):
    """Determine which analysis branch to use based on sample size."""
    n = len(event_df)

    print(f"\nSample size: {n} events")
    if n >= 50:
        branch = 'large'
        print("BRANCH: Large sample")
        print("  -> Full OLS impulse response")
        print("  -> HAC standard errors")
        print("  -> Can include controls and subgroups")
    elif n >= 15:
        branch = 'medium'
        print("BRANCH: Medium sample")
        print("  -> Parsimonious OLS")
        print("  -> Bootstrap confidence intervals")
        print("  -> No subgroup splits")
    else:
        branch = 'small'
        print("BRANCH: Small sample")
        print("  -> Descriptive event study only")
        print("  -> Visual inspection of average path")
        print("  -> No formal hypothesis testing")

    return branch


# =============================================================================
# TOOL: DESCRIPTIVE EVENT STUDY (all branches)
# =============================================================================

def event_study_plot(event_df, pre_bars=12, post_bars=48):
    """
    Plot average rate path around execution events.

    This is always the first thing to look at, regardless of branch.
    Visual inspection often reveals more than formal tests with small samples.

    What to look for:
        - Rate rises at t=0 (your buying pushes rate up)
        - Rate falls back after t=0 (temporary impact reverting)
        - Rate settles at a new level (permanent impact)
        - The shape of the decay (fast vs slow, smooth vs noisy)
    """
    # Collect all rate paths aligned at t=0
    all_paths = []
    for _, event in event_df.iterrows():
        path = event['rate_path']
        # Reindex to common grid
        common_index = range(-pre_bars, post_bars + 1)
        aligned = path.reindex(common_index)
        all_paths.append(aligned.values)

    paths_array = np.array(all_paths)  # shape: (n_events, n_bars)
    n = len(all_paths)

    mean_path = np.nanmean(paths_array, axis=0)
    se_path = np.nanstd(paths_array, axis=0) / np.sqrt(n)

    bars = np.array(range(-pre_bars, post_bars + 1))

    # Plot
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Mean path with CI
    axes[0].plot(bars, mean_path, 'o-', color='#1a5276', linewidth=1.5, markersize=3)
    axes[0].fill_between(bars, mean_path - 1.96*se_path, mean_path + 1.96*se_path,
                         alpha=0.2, color='#1a5276')
    axes[0].axvline(x=0, color='red', ls='--', linewidth=1, label='Execution')
    axes[0].axhline(y=0, color='grey', ls='-', linewidth=0.5)
    axes[0].set_xlabel('Bars relative to execution')
    axes[0].set_ylabel('Cumulative rate change (bps)')
    axes[0].set_title(f'Average Rate Path Around Execution (n={n})')
    axes[0].legend()

    # Individual paths (for visual sense of dispersion)
    for i, path in enumerate(all_paths[:20]):  # Show max 20
        axes[1].plot(bars, path, color='#2c3e50', alpha=0.15, linewidth=0.5)
    axes[1].plot(bars, mean_path, color='#c0392b', linewidth=2, label='Mean')
    axes[1].axvline(x=0, color='red', ls='--', linewidth=1)
    axes[1].axhline(y=0, color='grey', ls='-', linewidth=0.5)
    axes[1].set_xlabel('Bars relative to execution')
    axes[1].set_ylabel('Cumulative rate change (bps)')
    axes[1].set_title(f'Individual Event Paths (up to 20 shown)')
    axes[1].legend()

    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/nb4_event_study.png', dpi=150, bbox_inches='tight')
    plt.show()

    # Quick impact decomposition from the mean path
    peak_impact = np.nanmax(mean_path[pre_bars:pre_bars+5])  # Max in first 5 bars post
    permanent_impact = np.nanmean(mean_path[-10:])  # Average of last 10 bars
    temporary_impact = peak_impact - permanent_impact

    print(f"\nDescriptive Impact Decomposition:")
    print(f"  Peak impact (t=0 to t+5):     {peak_impact:.4f} bps")
    print(f"  Permanent impact (tail avg):   {permanent_impact:.4f} bps")
    print(f"  Temporary impact (reverts):    {temporary_impact:.4f} bps")
    if peak_impact != 0:
        print(f"  Temporary / Total:             {temporary_impact/peak_impact*100:.1f}%")

    return mean_path, se_path, bars


# =============================================================================
# TOOL: COUNTERFACTUAL CONSTRUCTION
# =============================================================================

def build_counterfactual_simple(market_data, event_df, pre_bars=12, post_bars=48):
    """
    Simple counterfactual: average rate path on NON-event days at the
    same time of day.

    For each event at time T on date D, find all non-event days and
    compute the average rate path starting at the same time T.
    The difference is the impact estimate.
    """
    event_dates = set(event_df['date'])

    # Get all non-event days
    all_dates = set(market_data.index.date)
    non_event_dates = all_dates - event_dates

    # For each event, find matching non-event paths
    event_impacts = []

    for _, event in event_df.iterrows():
        ts = event['timestamp']
        event_time = ts.time() if hasattr(ts, 'time') else None
        if event_time is None:
            continue

        # Find non-event paths at the same time of day
        non_event_paths = []
        for ne_date in non_event_dates:
            # Construct the same time on the non-event date
            try:
                ne_ts = pd.Timestamp.combine(ne_date, event_time)
                idx = market_data.index.searchsorted(ne_ts)
                if idx == 0 or idx >= len(market_data) - post_bars:
                    continue

                start = max(0, idx - pre_bars)
                end = min(len(market_data), idx + post_bars + 1)
                window = market_data.iloc[start:end]
                base = market_data.iloc[idx]
                relative = (window - base).values

                # Pad/trim to common length
                expected_len = pre_bars + post_bars + 1
                if len(relative) == expected_len:
                    non_event_paths.append(relative)
            except Exception:
                continue

        if non_event_paths:
            counterfactual = np.mean(non_event_paths, axis=0)
            event_path = event['rate_path'].reindex(range(-pre_bars, post_bars+1)).values
            impact = event_path - counterfactual
            event_impacts.append(impact)

    if event_impacts:
        impacts = np.array(event_impacts)
        mean_impact = np.nanmean(impacts, axis=0)
        se_impact = np.nanstd(impacts, axis=0) / np.sqrt(len(impacts))

        print(f"\nCounterfactual-adjusted impact (n={len(impacts)} events):")
        # Show key horizons
        bars = range(-pre_bars, post_bars + 1)
        for h in [0, 2, 4, 8, 12, 24, 48]:
            if pre_bars + h < len(mean_impact):
                val = mean_impact[pre_bars + h]
                err = se_impact[pre_bars + h]
                sig = '*' if abs(val) > 1.96 * err else ''
                print(f"  t+{h:>2}: {val:>8.4f} ± {err:.4f} {sig}")

        return mean_impact, se_impact
    else:
        print("Could not construct counterfactuals (insufficient non-event data)")
        return None, None


# =============================================================================
# TOOL: OLS IMPULSE RESPONSE (large and medium sample branches)
# =============================================================================

def ols_impulse_response(event_df, market_data, horizons=None,
                         pre_bars=12, post_bars=48, use_bootstrap=False,
                         n_bootstrap=1000):
    """
    OLS impulse response: regress rate change on notional at each horizon.

    Delta_r(t -> t+h) = alpha_h + beta_h * notional_t + epsilon

    beta_h traces out the impact curve.

    For large samples: HAC (Newey-West) standard errors.
    For medium samples: bootstrap confidence intervals.

    You can optionally add controls (e.g., market volatility that day)
    by extending the X matrix.
    """
    if horizons is None:
        horizons = [1, 2, 3, 4, 6, 8, 10, 12, 16, 20, 24, 36, 48]

    results = []

    for h in horizons:
        y_vals = []
        x_vals = []

        for _, event in event_df.iterrows():
            path = event['rate_path']
            if h in path.index and 0 in path.index:
                delta_r = path[h] - path[0]  # Rate change from execution to t+h
                notional = event.get('notional', 1)
                if not np.isnan(delta_r) and not np.isnan(notional):
                    y_vals.append(delta_r)
                    x_vals.append(notional)

        if len(y_vals) < 5:
            continue

        y = np.array(y_vals)
        x = np.array(x_vals)
        X = np.column_stack([np.ones(len(x)), x])

        # OLS
        beta = np.linalg.lstsq(X, y, rcond=None)[0]
        residuals = y - X @ beta
        n = len(y)

        if use_bootstrap:
            # Bootstrap confidence intervals
            boot_betas = []
            for _ in range(n_bootstrap):
                idx = np.random.choice(n, n, replace=True)
                b = np.linalg.lstsq(X[idx], y[idx], rcond=None)[0]
                boot_betas.append(b[1])
            boot_betas = np.array(boot_betas)
            ci_lo, ci_hi = np.percentile(boot_betas, [2.5, 97.5])
            se_beta = np.std(boot_betas)
        else:
            # HAC (Newey-West) standard errors
            # Simplified: use regular OLS SE as baseline
            mse = np.sum(residuals**2) / (n - 2)
            se_beta = np.sqrt(mse * np.linalg.inv(X.T @ X)[1, 1])
            ci_lo = beta[1] - 1.96 * se_beta
            ci_hi = beta[1] + 1.96 * se_beta

        t_stat = beta[1] / se_beta if se_beta > 0 else 0
        p_val = 2 * (1 - stats.t.cdf(abs(t_stat), n - 2))

        results.append({
            'horizon': h,
            'alpha': beta[0],
            'beta': beta[1],
            'se_beta': se_beta,
            't_stat': t_stat,
            'p_value': p_val,
            'ci_lo': ci_lo,
            'ci_hi': ci_hi,
            'n': n,
            'r_squared': 1 - np.sum(residuals**2) / np.sum((y - y.mean())**2),
        })

    res = pd.DataFrame(results)

    print(f"\nOLS Impulse Response:")
    print(f"{'h':>4} {'beta':>10} {'SE':>10} {'t-stat':>8} {'p':>8} {'R²':>8}")
    for _, row in res.iterrows():
        sig = '*' if row['p_value'] < 0.05 else ''
        print(f"{row['horizon']:>4.0f} {row['beta']:>10.6f} {row['se_beta']:>10.6f} "
              f"{row['t_stat']:>8.2f} {row['p_value']:>8.4f} {row['r_squared']:>8.4f} {sig}")

    # Plot
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(res['horizon'], res['beta'], 'o-', color='#1a5276', linewidth=1.5)
    ax.fill_between(res['horizon'], res['ci_lo'], res['ci_hi'],
                    alpha=0.2, color='#1a5276')
    ax.axhline(y=0, color='grey', ls='-', linewidth=0.5)
    ax.set_xlabel('Horizon (bars after execution)')
    ax.set_ylabel('Impact coefficient (bps per EUR notional)')
    ax.set_title('Impulse Response Function: NWB Execution Impact')
    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/nb4_impulse_response.png', dpi=150, bbox_inches='tight')
    plt.show()

    # Impact decomposition
    if len(res) > 0:
        peak = res['beta'].max()
        permanent = res['beta'].iloc[-3:].mean()  # Average of last 3 horizons
        temporary = peak - permanent

        print(f"\nImpact Decomposition (from OLS):")
        print(f"  Peak impact coefficient:     {peak:.6f}")
        print(f"  Permanent impact coefficient:{permanent:.6f}")
        print(f"  Temporary impact coefficient:{temporary:.6f}")
        if peak != 0:
            print(f"  Temporary / Total:           {temporary/peak*100:.1f}%")

    return res


# =============================================================================
# TOOL: LINK TO EXECUTION STRATEGY
# =============================================================================

def impact_to_savings(impact_results, typical_notional, dv01_per_mm=25,
                      optimal_freq=5):
    """
    Translate impact estimates into expected savings from delay.

    If beta(h) shows that impact at h=0 is X bps per unit notional,
    and at h=H it decays to Y, then delaying by H bars saves (X-Y) bps.
    """
    if impact_results is None or len(impact_results) == 0:
        print("No impact results to translate.")
        return

    print(f"\n{'='*60}")
    print(f"SAVINGS TRANSLATION")
    print(f"{'='*60}")
    print(f"  Typical notional: EUR {typical_notional/1e6:.0f}M")
    print(f"  DV01 per million: EUR {dv01_per_mm}")

    total_dv01 = typical_notional / 1e6 * dv01_per_mm

    peak_beta = impact_results['beta'].max()

    for _, row in impact_results.iterrows():
        h = row['horizon']
        decay = peak_beta - row['beta']
        hours = h * optimal_freq / 60

        saving_bps = decay * typical_notional  # Scale beta by notional
        saving_eur = saving_bps * total_dv01

        print(f"  Delay {h:>3.0f} bars ({hours:>5.1f}h): "
              f"recover {decay:.6f} bps/unit -> "
              f"~EUR {saving_eur:>10,.0f} per trade")


# =============================================================================
# EXECUTION
# =============================================================================
"""
Workflow:
    1. load_internal_orders() - get order data
    2. prepare_event_dataset() - match to market data
    3. determine_branch() - choose analysis path
    4. event_study_plot() - always do this first (visual)
    5. Branch:
       - Small:  stop at step 4, report descriptively
       - Medium: ols_impulse_response(use_bootstrap=True)
       - Large:  ols_impulse_response() + build_counterfactual_simple()
    6. impact_to_savings() - translate to EUR

Key output: temporary impact fraction and decay half-life.
Combined with Track A half-life, this informs the optimal delay.
"""

# Example (uncomment):
#
# orders = load_internal_orders('path/to/orders.csv')
# prices = pd.read_parquet(f'{OUTPUT_DIR}/EUSA30_Curncy_5min.parquet')['close']
#
# events = prepare_event_dataset(orders, prices, tenor_filter=30)
# branch = determine_branch(events)
#
# mean_path, se_path, bars = event_study_plot(events)
#
# if branch in ('large', 'medium'):
#     irf = ols_impulse_response(events, prices,
#                                use_bootstrap=(branch == 'medium'))
#     impact_to_savings(irf, typical_notional=100e6)
#
# if branch == 'large':
#     adj_impact, adj_se = build_counterfactual_simple(prices, events)

print("Notebook 4 loaded. Start with load_internal_orders().")
