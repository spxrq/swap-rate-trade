"""
================================================================================
NOTEBOOK 5: EXECUTION SIMULATION & COST-BENEFIT (TRACKS A + B + C)
================================================================================
Purpose:
    Simulate execution strategies using findings from Tracks A and B.
    Quantify expected savings, risk, and build the business case.

    This notebook only runs AFTER Tracks A and/or B have shown positive results.

Prerequisite:
    - Track A (Notebook 3): half-life estimate and model specification
    - Track B (Notebook 4): impact decomposition (if available)
    - Market data at chosen frequency

Strategies tested:
    1. Baseline: execute 100% at T=0
    2. Full delay: execute 100% at T=0+delay
    3. Split execution: X% at T=0, (1-X)% at T=0+delay
    4. Optimal window: execute at best time of day (from EDA)
    5. Adaptive: condition delay on volatility / volume (Track C extension)

For each strategy, compute:
    - Mean saving (bps)
    - Risk (std dev of saving)
    - Sharpe-like ratio
    - VaR / CVaR of worst-case outcomes
    - Annual EUR savings with confidence intervals
================================================================================
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
import json
import os

OUTPUT_DIR = './swap_research'


# =============================================================================
# TOOL: EXECUTION SIMULATION ENGINE
# =============================================================================

def simulate_delay_strategy(market_data, delays, execute_bar=6):
    """
    Simulate delaying full execution by various amounts.

    For each trading day:
        - Baseline: execute at bar execute_bar (e.g., 30 min after open)
        - Delayed: execute at bar execute_bar + delay

    The "saving" is the rate difference: baseline_rate - delayed_rate.
    For a PAYER (paying fixed), lower rate = better, so positive saving
    means the delay helped.

    Parameters
    ----------
    market_data : Series of rates at chosen frequency
    delays      : list of delay values in bars
    execute_bar : which bar within the day to use as baseline execution
    """
    daily = market_data.groupby(market_data.index.date)
    results = {}

    for delay in delays:
        savings = []
        dates = []

        for date, group in daily:
            rates = group.values
            if execute_bar + delay >= len(rates):
                continue

            rate_baseline = rates[execute_bar]
            rate_delayed = rates[execute_bar + delay]
            saving = rate_baseline - rate_delayed
            savings.append(saving)
            dates.append(date)

        s = np.array(savings)
        results[delay] = {
            'delay_bars': delay,
            'savings': s,
            'dates': dates,
            'mean': np.mean(s),
            'std': np.std(s),
            'median': np.median(s),
            'pct_positive': (s > 0).mean() * 100,
            'sharpe': np.mean(s) / np.std(s) if np.std(s) > 0 else 0,
            'var_5': np.percentile(s, 5),
            'cvar_5': np.mean(s[s <= np.percentile(s, 5)]) if len(s) > 20 else np.nan,
            'max_loss': np.min(s),
            'max_gain': np.max(s),
            'n_days': len(s),
        }

    return results


def simulate_split_strategy(market_data, delay, split_ratios,
                            execute_bar=6):
    """
    Split execution: do split_ratio at T=0, rest at T+delay.
    More conservative than full delay. Test different split ratios.
    """
    daily = market_data.groupby(market_data.index.date)
    results = {}

    for ratio in split_ratios:
        savings = []

        for date, group in daily:
            rates = group.values
            if execute_bar + delay >= len(rates):
                continue

            rate_t0 = rates[execute_bar]
            rate_delayed = rates[execute_bar + delay]

            # Blended rate
            blended = ratio * rate_t0 + (1 - ratio) * rate_delayed
            saving = rate_t0 - blended  # Positive = saved vs full T=0
            savings.append(saving)

        s = np.array(savings)
        results[ratio] = {
            'split_ratio': ratio,
            'delay': delay,
            'savings': s,
            'mean': np.mean(s),
            'std': np.std(s),
            'sharpe': np.mean(s) / np.std(s) if np.std(s) > 0 else 0,
            'pct_positive': (s > 0).mean() * 100,
        }

    return results


def simulate_optimal_window(market_data):
    """
    For each day, find the best execution time (lowest rate for a payer).
    Compare to fixed-time execution.

    This gives the theoretical maximum saving if you had perfect foresight.
    Obviously not achievable, but sets an upper bound.
    """
    daily = market_data.groupby(market_data.index.date)
    records = []

    for date, group in daily:
        if len(group) < 20:
            continue

        rates = group.values
        hours = group.index.hour + group.index.minute / 60

        records.append({
            'date': date,
            'open_rate': rates[0],
            'morning_rate': np.mean(rates[:len(rates)//3]),
            'midday_rate': np.mean(rates[len(rates)//3:2*len(rates)//3]),
            'afternoon_rate': np.mean(rates[2*len(rates)//3:]),
            'daily_min': np.min(rates),
            'daily_max': np.max(rates),
            'min_hour': hours[np.argmin(rates)],
            'range': np.max(rates) - np.min(rates),
        })

    df = pd.DataFrame(records)

    print(f"\nOptimal Window Analysis ({len(df)} days):")
    print(f"  Mean morning rate:   {df['morning_rate'].mean():.4f}")
    print(f"  Mean midday rate:    {df['midday_rate'].mean():.4f}")
    print(f"  Mean afternoon rate: {df['afternoon_rate'].mean():.4f}")
    print(f"  Mean daily range:    {df['range'].mean():.4f} bps")
    print(f"  Avg hour of daily min: {df['min_hour'].mean():.1f}")

    # Histogram of best execution time
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    axes[0].hist(df['min_hour'], bins=20, color='#27ae60', alpha=0.7, edgecolor='white')
    axes[0].set_xlabel('Hour of day (CET)')
    axes[0].set_ylabel('Frequency')
    axes[0].set_title('Distribution of Best Execution Time')

    # Compare fixed windows
    windows = ['morning_rate', 'midday_rate', 'afternoon_rate']
    means = [df[w].mean() for w in windows]
    axes[1].bar(['Morning', 'Midday', 'Afternoon'], means,
                color=['#3498db', '#e74c3c', '#2ecc71'], alpha=0.7)
    axes[1].set_ylabel('Average rate')
    axes[1].set_title('Average Rate by Time Window')

    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/nb5_optimal_window.png', dpi=150, bbox_inches='tight')
    plt.show()

    return df


# =============================================================================
# TOOL: TRACK C EXTENSION - CONDITIONAL STRATEGIES
# =============================================================================

def conditional_on_volatility(market_data, delay=12, execute_bar=6,
                              vol_lookback=20):
    """
    Track C extension: does the delay strategy work better in
    low-vol or high-vol environments?

    Compute rolling volatility, split days into high/low vol,
    and compare strategy performance in each regime.
    """
    returns = market_data.diff().dropna()
    daily_vol = returns.groupby(returns.index.date).std()

    # Rolling vol for regime classification
    rolling_vol = daily_vol.rolling(vol_lookback).mean()

    median_vol = rolling_vol.median()
    high_vol_days = set(rolling_vol[rolling_vol >= median_vol].index)
    low_vol_days = set(rolling_vol[rolling_vol < median_vol].index)

    # Simulate delay strategy in each regime
    daily = market_data.groupby(market_data.index.date)

    regimes = {'high_vol': [], 'low_vol': []}

    for date, group in daily:
        rates = group.values
        if execute_bar + delay >= len(rates):
            continue

        saving = rates[execute_bar] - rates[execute_bar + delay]

        if date in high_vol_days:
            regimes['high_vol'].append(saving)
        elif date in low_vol_days:
            regimes['low_vol'].append(saving)

    print(f"\nVolatility-Conditional Strategy Performance (delay={delay}):")
    for regime, savings in regimes.items():
        if len(savings) < 5:
            print(f"  {regime}: insufficient data ({len(savings)} days)")
            continue
        s = np.array(savings)
        print(f"  {regime}:")
        print(f"    N days:       {len(s)}")
        print(f"    Mean saving:  {np.mean(s):.4f} bps")
        print(f"    Std:          {np.std(s):.4f} bps")
        print(f"    Sharpe:       {np.mean(s)/np.std(s):.3f}")
        print(f"    Win rate:     {(s > 0).mean()*100:.1f}%")

    # Statistical test: is the difference significant?
    if len(regimes['high_vol']) >= 10 and len(regimes['low_vol']) >= 10:
        t_stat, p_val = stats.ttest_ind(regimes['low_vol'], regimes['high_vol'])
        print(f"\n  Difference test (low vs high vol): t={t_stat:.2f}, p={p_val:.4f}")
        if p_val < 0.05:
            print("  -> Significant difference. Adaptive strategy warranted.")
            print("     RECOMMENDATION: increase delay in low-vol, reduce in high-vol")
        else:
            print("  -> No significant difference. Unconditional strategy is fine.")

    return regimes


def conditional_on_time_of_day(market_data, delays=[4, 8, 12],
                               morning_bar=6, afternoon_bar=36):
    """
    Track C extension: does delaying from morning to afternoon
    work better than delaying within the morning?

    Compare:
        A) Execute at morning_bar, delay within morning
        B) Execute at morning_bar, delay to afternoon
    """
    daily = market_data.groupby(market_data.index.date)

    morning_to_afternoon = []
    for date, group in daily:
        rates = group.values
        if afternoon_bar >= len(rates) or morning_bar >= len(rates):
            continue
        saving = rates[morning_bar] - rates[afternoon_bar]
        morning_to_afternoon.append(saving)

    s = np.array(morning_to_afternoon)
    print(f"\nMorning-to-Afternoon Shift:")
    print(f"  Mean saving: {np.mean(s):.4f} bps")
    print(f"  Std:         {np.std(s):.4f} bps")
    print(f"  Win rate:    {(s > 0).mean()*100:.1f}%")
    print(f"  Sharpe:      {np.mean(s)/np.std(s):.3f}")

    return s


# =============================================================================
# TOOL: COST-BENEFIT ANALYSIS
# =============================================================================

def full_cost_benefit(strategy_results, notional_per_trade,
                      trades_per_year, dv01_per_mm=25, optimal_freq=5):
    """
    Translate simulation results into business case numbers.

    For each strategy, compute:
        - Expected annual savings in EUR
        - 95% confidence interval on annual savings
        - VaR: worst-case per-trade loss
        - Break-even win rate
    """
    total_dv01 = notional_per_trade / 1e6 * dv01_per_mm

    print(f"\n{'='*60}")
    print(f"COST-BENEFIT ANALYSIS")
    print(f"{'='*60}")
    print(f"  Notional per trade: EUR {notional_per_trade/1e6:.0f}M")
    print(f"  Trades per year:    {trades_per_year}")
    print(f"  DV01 per million:   EUR {dv01_per_mm}")
    print(f"  Total DV01/trade:   EUR {total_dv01:,.0f}")

    for key, s in strategy_results.items():
        savings = s['savings']
        mean_bps = s['mean']
        std_bps = s['std']
        n = len(savings)

        # Per-trade EUR
        mean_eur = mean_bps * total_dv01
        std_eur = std_bps * total_dv01

        # Annual
        annual_mean = mean_eur * trades_per_year
        annual_std = std_eur * np.sqrt(trades_per_year)

        # Confidence interval on mean
        se = std_bps / np.sqrt(n)
        ci_lo_bps = mean_bps - 1.96 * se
        ci_hi_bps = mean_bps + 1.96 * se

        # Break-even
        gains = savings[savings > 0]
        losses = savings[savings <= 0]
        avg_gain = np.mean(gains) if len(gains) > 0 else 0
        avg_loss = np.mean(np.abs(losses)) if len(losses) > 0 else 0
        break_even = avg_loss / (avg_gain + avg_loss) * 100 if (avg_gain + avg_loss) > 0 else 50

        hours = key * optimal_freq / 60 if isinstance(key, (int, float)) else key

        print(f"\n  --- Delay: {key} bars ({hours:.1f}h) ---")
        print(f"  Per trade:")
        print(f"    Mean saving:    {mean_bps:.4f} bps  (EUR {mean_eur:>10,.0f})")
        print(f"    95% CI:         [{ci_lo_bps:.4f}, {ci_hi_bps:.4f}] bps")
        print(f"    Std:            {std_bps:.4f} bps  (EUR {std_eur:>10,.0f})")
        print(f"    Win rate:       {s['pct_positive']:.1f}%")
        print(f"    Break-even:     {break_even:.1f}%")
        print(f"    Sharpe:         {s['sharpe']:.3f}")
        print(f"    Worst trade:    {s['max_loss']:.4f} bps")
        if not np.isnan(s.get('cvar_5', np.nan)):
            print(f"    CVaR(5%):       {s['cvar_5']:.4f} bps")
        print(f"  Annual:")
        print(f"    Expected:       EUR {annual_mean:>12,.0f}")
        print(f"    CI:             EUR [{ci_lo_bps*total_dv01*trades_per_year:>10,.0f}, "
              f"{ci_hi_bps*total_dv01*trades_per_year:>10,.0f}]")


def summary_visualization(strategy_results, optimal_freq=5):
    """Final summary chart for presentation."""
    delays = sorted(strategy_results.keys())
    means = [strategy_results[d]['mean'] for d in delays]
    stds = [strategy_results[d]['std'] for d in delays]
    sharpes = [strategy_results[d]['sharpe'] for d in delays]
    hours = [d * optimal_freq / 60 for d in delays]

    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    # Mean saving
    colors = ['#27ae60' if m > 0 else '#c0392b' for m in means]
    axes[0].bar(range(len(delays)), means, yerr=stds, color=colors,
                alpha=0.7, capsize=4)
    axes[0].set_xticks(range(len(delays)))
    axes[0].set_xticklabels([f'{h:.1f}h' for h in hours])
    axes[0].axhline(y=0, color='black', linewidth=0.5)
    axes[0].set_xlabel('Delay')
    axes[0].set_ylabel('Mean saving (bps)')
    axes[0].set_title('Expected Saving by Delay')

    # Sharpe ratio
    axes[1].bar(range(len(delays)), sharpes, color='#2980b9', alpha=0.7)
    axes[1].set_xticks(range(len(delays)))
    axes[1].set_xticklabels([f'{h:.1f}h' for h in hours])
    axes[1].set_xlabel('Delay')
    axes[1].set_ylabel('Sharpe ratio')
    axes[1].set_title('Risk-Adjusted Performance')

    # Best strategy distribution
    best = max(delays, key=lambda d: strategy_results[d]['sharpe'])
    s = strategy_results[best]['savings']
    axes[2].hist(s, bins=40, color='#2c3e50', alpha=0.7, density=True,
                 edgecolor='white')
    axes[2].axvline(x=0, color='red', ls='--', linewidth=1)
    axes[2].axvline(x=np.mean(s), color='green', ls='--', linewidth=1.5,
                    label=f'Mean: {np.mean(s):.4f}')
    axes[2].set_xlabel('Saving (bps)')
    axes[2].set_title(f'Best Strategy Distribution (delay={best} bars)')
    axes[2].legend()

    plt.suptitle('Execution Timing Strategy Results', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/nb5_summary.png', dpi=150, bbox_inches='tight')
    plt.show()


# =============================================================================
# EXECUTION
# =============================================================================
"""
Workflow:
    1. Load market data at chosen frequency
    2. simulate_delay_strategy() - test multiple delay horizons
    3. simulate_split_strategy() - test conservative splits
    4. simulate_optimal_window() - benchmark against theoretical best
    5. Track C extensions (if warranted):
       - conditional_on_volatility()
       - conditional_on_time_of_day()
    6. full_cost_benefit() - translate to EUR
    7. summary_visualization() - chart for presentation

The output is the business case: which strategy, expected savings,
risk metrics, and recommendation.
"""

# Example (uncomment):
#
# prices = pd.read_parquet(f'{OUTPUT_DIR}/EUSA30_Curncy_5min.parquet')['close']
# OPTIMAL_FREQ = 5
#
# # Full delay strategies
# delay_results = simulate_delay_strategy(prices, delays=[4, 8, 12, 24, 36, 48])
#
# # Split strategies (with best delay from above)
# best_delay = max(delay_results, key=lambda d: delay_results[d]['sharpe'])
# split_results = simulate_split_strategy(prices, best_delay,
#                                          split_ratios=[0.3, 0.5, 0.7])
#
# # Optimal window benchmark
# window_df = simulate_optimal_window(prices)
#
# # Track C (if Track A showed regime-dependent mean reversion)
# # vol_regimes = conditional_on_volatility(prices, delay=best_delay)
# # tod_savings = conditional_on_time_of_day(prices)
#
# # Business case
# full_cost_benefit(delay_results,
#                   notional_per_trade=100e6,  # Adjust to NWB actuals
#                   trades_per_year=16,         # Adjust
#                   dv01_per_mm=25,
#                   optimal_freq=OPTIMAL_FREQ)
#
# summary_visualization(delay_results, OPTIMAL_FREQ)

print("Notebook 5 loaded. Run after Tracks A and/or B are complete.")
