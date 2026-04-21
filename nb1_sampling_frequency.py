"""
================================================================================
NOTEBOOK 1: OPTIMAL SAMPLING FREQUENCY
================================================================================
Purpose:
    Determine the sampling frequency at which microstructure noise is
    sufficiently attenuated but information loss is acceptable.
    This decision constrains ALL downstream analysis.

Prerequisite:
    Notebook 0 complete. At least one tenor of 1-minute bar data pulled
    and saved to ./swap_research/

Decision output:
    A single number per tenor: the optimal bar size in minutes.
    If the signature plot never stabilizes -> flag that tenor as unsuitable.

Tools used:
    - Realized variance (RV)
    - Bi-power variation (BPV)
    - Relative jump measure
    - Hansen & Lunde (2006) noise variance estimator
    - Bandi & Russell (2008) optimal frequency
    - Signature plot visualization
================================================================================
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
import os

OUTPUT_DIR = './swap_research'


# =============================================================================
# TOOL: REALIZED VARIANCE & BI-POWER VARIATION
# =============================================================================

def realized_variance(returns):
    """
    RV = sum(r_i^2)

    Standard non-parametric volatility estimator.
    At very high frequencies, RV is biased upward by microstructure noise.
    """
    return np.sum(returns ** 2)


def bipower_variation(returns):
    """
    BPV = (pi/2) * sum(|r_i| * |r_{i-1}|)

    Barndorff-Nielsen & Shephard (2004).
    Consistent estimator of integrated variance even in the presence of jumps.
    Comparing RV to BPV tells you how much of the variation is jump-driven.
    """
    mu_1 = np.sqrt(2 / np.pi)  # E[|Z|] for Z ~ N(0,1)
    abs_ret = np.abs(returns)
    return (1 / mu_1**2) * np.sum(abs_ret[1:] * abs_ret[:-1])


def relative_jump_measure(returns):
    """
    J = max(0, (RV - BPV) / RV)

    Proportion of total variance attributable to jumps.
    High values at low frequency -> genuine discontinuities in the rate.
    High values at high frequency -> likely noise, not real jumps.
    """
    rv = realized_variance(returns)
    bpv = bipower_variation(returns)
    if rv == 0:
        return 0.0
    return max(0.0, (rv - bpv) / rv)


# =============================================================================
# TOOL: NOISE VARIANCE ESTIMATION
# =============================================================================

def noise_variance_hansen_lunde(returns):
    """
    Hansen & Lunde (2006) noise variance estimator.

    Under the model: observed_price = efficient_price + noise
    The first-order autocovariance of returns at the highest available
    frequency gives a consistent estimate of noise variance:

        Var(noise) ≈ -Cov(r_t, r_{t+1})

    Interpretation:
        - Large noise variance -> need to sample at lower frequency
        - Small noise variance -> high-frequency data is usable
        - Negative estimate -> model assumption may be violated
          (could indicate positive autocorrelation, i.e., momentum at
          tick level, which is unusual for swaps)
    """
    if len(returns) < 10:
        return np.nan

    gamma_1 = np.cov(returns[:-1], returns[1:])[0, 1]
    noise_var = -gamma_1

    return noise_var


def noise_variance_by_day(df_1min):
    """
    Estimate noise variance per day, then summarize.
    Day-to-day variation tells you if noise is stable or regime-dependent.
    """
    returns = df_1min['close'].diff().dropna()
    daily_noise = []

    for date, group in returns.groupby(returns.index.date):
        r = group.values
        if len(r) < 20:
            continue
        nv = noise_variance_hansen_lunde(r)
        daily_noise.append({'date': date, 'noise_var': nv})

    nv_df = pd.DataFrame(daily_noise)

    print(f"\nNoise Variance (Hansen-Lunde) Summary:")
    print(f"  Mean:   {nv_df['noise_var'].mean():.8f}")
    print(f"  Median: {nv_df['noise_var'].median():.8f}")
    print(f"  Std:    {nv_df['noise_var'].std():.8f}")
    print(f"  Pct negative: {(nv_df['noise_var'] < 0).mean()*100:.1f}%")

    if (nv_df['noise_var'] < 0).mean() > 0.3:
        print("\n  NOTE: Many days have negative noise variance estimates.")
        print("  This suggests the i.i.d. noise assumption may not hold,")
        print("  or that there is genuine positive autocorrelation at 1-min.")
        print("  The signature plot is more reliable in this case.")

    return nv_df


# =============================================================================
# TOOL: SIGNATURE PLOT
# =============================================================================

def resample_to_bars(df_1min, freq_minutes):
    """Resample 1-min data to larger bars. Uses close of each bar."""
    rule = f'{freq_minutes}min'
    resampled = df_1min['close'].resample(rule).last().dropna()
    return resampled


def signature_plot(df_1min, frequencies=None):
    """
    Signature plot: realized variance as a function of sampling frequency.

    How to read it:
        - At very high frequencies (1-2 min), RV is inflated by noise.
        - As frequency decreases, RV drops and eventually stabilizes.
        - The frequency where RV flattens out is the minimum bar size
          at which noise is no longer dominant.
        - If RV keeps changing even at 30-60 min, the data may be too
          noisy for reliable intraday analysis at any frequency.

    We also plot BPV alongside RV. The gap between them at high frequency
    indicates how much of the apparent variation is noise/jumps vs signal.
    """
    if frequencies is None:
        frequencies = [1, 2, 3, 5, 7, 10, 15, 20, 30, 45, 60]

    results = []

    for freq in frequencies:
        resampled = resample_to_bars(df_1min, freq)
        daily_groups = resampled.groupby(resampled.index.date)

        daily_rv, daily_bpv, daily_jump, daily_n = [], [], [], []

        for date, group in daily_groups:
            returns = group.diff().dropna().values
            if len(returns) < 5:
                continue
            daily_rv.append(realized_variance(returns))
            daily_bpv.append(bipower_variation(returns))
            daily_jump.append(relative_jump_measure(returns))
            daily_n.append(len(returns))

        if not daily_rv:
            continue

        results.append({
            'freq_min': freq,
            'bars_per_day': np.mean(daily_n),
            'rv_mean': np.mean(daily_rv),
            'rv_std': np.std(daily_rv),
            'rv_median': np.median(daily_rv),
            'bpv_mean': np.mean(daily_bpv),
            'bpv_std': np.std(daily_bpv),
            'jump_mean': np.mean(daily_jump),
            'n_days': len(daily_rv),
        })

    res = pd.DataFrame(results)

    # -- Visualization
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # 1. Signature plot (RV)
    axes[0, 0].errorbar(res['freq_min'], res['rv_mean'],
                        yerr=res['rv_std'] / np.sqrt(res['n_days']),
                        fmt='o-', color='#1a5276', capsize=3, linewidth=1.5)
    axes[0, 0].set_xlabel('Sampling frequency (minutes)')
    axes[0, 0].set_ylabel('Mean daily RV')
    axes[0, 0].set_title('Signature Plot: Realized Variance')
    axes[0, 0].set_xscale('log')
    axes[0, 0].grid(True, alpha=0.3)

    # 2. RV vs BPV
    axes[0, 1].plot(res['freq_min'], res['rv_mean'], 'o-',
                    label='RV', color='#1a5276', linewidth=1.5)
    axes[0, 1].plot(res['freq_min'], res['bpv_mean'], 's--',
                    label='BPV', color='#c0392b', linewidth=1.5)
    axes[0, 1].set_xlabel('Sampling frequency (minutes)')
    axes[0, 1].set_ylabel('Mean daily estimate')
    axes[0, 1].set_title('RV vs Bi-Power Variation')
    axes[0, 1].legend()
    axes[0, 1].set_xscale('log')
    axes[0, 1].grid(True, alpha=0.3)

    # 3. RV/BPV ratio (noise indicator)
    ratio = res['rv_mean'] / res['bpv_mean']
    axes[1, 0].plot(res['freq_min'], ratio, 'o-', color='#8e44ad', linewidth=1.5)
    axes[1, 0].axhline(y=1.0, ls='--', color='grey', alpha=0.5)
    axes[1, 0].set_xlabel('Sampling frequency (minutes)')
    axes[1, 0].set_ylabel('RV / BPV')
    axes[1, 0].set_title('Noise Indicator: RV/BPV Ratio (→ 1.0 = clean)')
    axes[1, 0].set_xscale('log')
    axes[1, 0].grid(True, alpha=0.3)

    # 4. Jump contribution
    axes[1, 1].bar(range(len(res)), res['jump_mean'], color='#2c3e50', alpha=0.7)
    axes[1, 1].set_xticks(range(len(res)))
    axes[1, 1].set_xticklabels([f"{f}m" for f in res['freq_min']], rotation=45)
    axes[1, 1].set_xlabel('Sampling frequency')
    axes[1, 1].set_ylabel('Mean jump ratio')
    axes[1, 1].set_title('Relative Jump Contribution')

    plt.suptitle('Microstructure Noise Diagnostics', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/nb1_signature_plot.png', dpi=150, bbox_inches='tight')
    plt.show()

    return res


# =============================================================================
# TOOL: BANDI-RUSSELL OPTIMAL FREQUENCY
# =============================================================================

def bandi_russell_optimal_freq(df_1min, noise_var=None):
    """
    Bandi & Russell (2008) optimal sampling frequency.

    Minimizes MSE of RV estimator by balancing:
        - Bias from noise (favors lower frequency)
        - Variance from fewer observations (favors higher frequency)

    Optimal number of observations per day:
        n* = (8 * T * IQV / (3 * eta^4))^(1/3)

    where:
        T   = number of highest-frequency returns per day
        IQV = integrated quarticity (estimated via realized quarticity)
        eta = noise standard deviation

    Interpretation:
        n* gives you the ideal number of bars per day.
        Divide trading minutes by n* to get bar size in minutes.
    """
    returns_1min = df_1min['close'].diff().dropna()

    if noise_var is None:
        nv_df = noise_variance_by_day(df_1min)
        noise_var = max(nv_df['noise_var'].median(), 1e-12)

    daily_optimal_n = []

    for date, group in returns_1min.groupby(returns_1min.index.date):
        r = group.values
        if len(r) < 30:
            continue

        T = len(r)
        # Realized quarticity: (T/3) * sum(r^4)
        rq = (T / 3) * np.sum(r ** 4)

        if noise_var > 0:
            n_star = (8 * T * rq / (3 * noise_var ** 2)) ** (1/3)
            daily_optimal_n.append(n_star)

    if not daily_optimal_n:
        print("Insufficient data for Bandi-Russell estimate.")
        return None

    avg_n = np.mean(daily_optimal_n)
    trading_minutes = 10 * 60  # Approximate: 07:30 - 17:30
    optimal_bar_size = trading_minutes / avg_n

    print(f"\nBandi-Russell Optimal Frequency:")
    print(f"  Optimal bars per day: {avg_n:.0f}")
    print(f"  Implied bar size: {optimal_bar_size:.1f} minutes")
    print(f"  (Based on noise variance = {noise_var:.8f})")

    # Sanity check
    if optimal_bar_size < 1:
        print("\n  NOTE: Suggests sub-minute optimal frequency.")
        print("  This likely means noise variance is very low,")
        print("  or the quarticity estimate is high (jumpy days).")
        print("  Use the signature plot as the primary guide instead.")
    elif optimal_bar_size > 30:
        print("\n  NOTE: Suggests 30+ minute bars.")
        print("  This limits intraday observations severely.")
        print("  Check if the tenor is too illiquid for intraday work.")

    return optimal_bar_size


# =============================================================================
# DECISION FRAMEWORK
# =============================================================================

def decide_optimal_frequency(sig_results, bandi_russell_freq=None):
    """
    Combine signature plot and Bandi-Russell to choose bar size.

    Decision rules:
        1. From the signature plot, find the frequency where RV/BPV ratio
           first drops below 1.1 (i.e., noise contributes < 10% excess).
        2. Cross-check with Bandi-Russell estimate.
        3. Round to a "standard" bar size (1, 2, 5, 10, 15, 30 min)
           since Bloomberg provides data at these intervals.

    The final choice should also consider:
        - Bars per day: need enough for daily estimation.
          Minimum ~30 bars/day for meaningful within-day statistics.
        - Consistency: ideally same frequency across tenors for comparability.
    """
    # Find where RV/BPV ratio stabilizes
    ratio = sig_results['rv_mean'] / sig_results['bpv_mean']
    threshold = 1.1

    stable_idx = ratio[ratio < threshold].index
    if len(stable_idx) > 0:
        first_stable = stable_idx[0]
        freq_from_plot = sig_results.loc[first_stable, 'freq_min']
    else:
        freq_from_plot = sig_results['freq_min'].max()
        print("WARNING: RV/BPV never drops below 1.1. Data may be very noisy.")

    print(f"\nSignature plot suggests: >= {freq_from_plot} minute bars")
    if bandi_russell_freq:
        print(f"Bandi-Russell suggests: ~{bandi_russell_freq:.1f} minute bars")

    # Recommend the larger of the two (more conservative)
    candidates = [freq_from_plot]
    if bandi_russell_freq:
        candidates.append(bandi_russell_freq)
    recommendation = max(candidates)

    # Round to standard bar size
    standard_sizes = [1, 2, 3, 5, 10, 15, 20, 30, 60]
    chosen = min(standard_sizes, key=lambda x: abs(x - recommendation) if x >= recommendation * 0.8 else 999)

    bars_per_day = 600 / chosen  # ~10 hours
    print(f"\nRECOMMENDATION: {chosen}-minute bars")
    print(f"  (~{bars_per_day:.0f} bars per trading day)")

    if bars_per_day < 30:
        print("  WARNING: Fewer than 30 bars per day.")
        print("  Within-day model estimation will have limited power.")
        print("  Consider whether daily-frequency analysis (Track A at daily)")
        print("  might be more appropriate for this tenor.")

    return chosen


# =============================================================================
# MULTI-TENOR COMPARISON
# =============================================================================

def compare_tenors(data_dict, frequencies=None):
    """
    Run signature plot analysis for multiple tenors side by side.

    This answers: do different tenors have different noise characteristics?
    Longer/more illiquid tenors likely need coarser sampling.
    """
    if frequencies is None:
        frequencies = [1, 2, 5, 10, 15, 30, 60]

    fig, ax = plt.subplots(figsize=(10, 6))

    optimal_freqs = {}

    for ticker, df in data_dict.items():
        tenor = ticker.replace('EUSA', '').replace(' Curncy', '') + 'Y'
        sig = signature_plot.__wrapped__(df, frequencies) if hasattr(signature_plot, '__wrapped__') else None

        # Simplified: just compute RV at each frequency
        rvs = []
        for freq in frequencies:
            resampled = resample_to_bars(df, freq)
            returns = resampled.diff().dropna().values
            if len(returns) > 0:
                rvs.append(realized_variance(returns) / (len(returns) / 120))  # Normalize by days
            else:
                rvs.append(np.nan)

        ax.plot(frequencies, rvs, 'o-', label=tenor, linewidth=1.5)

    ax.set_xlabel('Sampling frequency (minutes)')
    ax.set_ylabel('Normalized RV')
    ax.set_title('Signature Plot Comparison Across Tenors')
    ax.set_xscale('log')
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.savefig(f'{OUTPUT_DIR}/nb1_tenor_comparison.png', dpi=150, bbox_inches='tight')
    plt.show()


# =============================================================================
# EXECUTION
# =============================================================================
"""
Workflow:
    1. Load 1-minute data from Notebook 0
    2. Run signature_plot() - visually inspect where RV stabilizes
    3. Run noise_variance_by_day() - check noise level and stability
    4. Run bandi_russell_optimal_freq() - get analytical recommendation
    5. Run decide_optimal_frequency() - combine evidence into a choice
    6. If multiple tenors available, run compare_tenors()
    7. Save chosen frequency for use in Notebook 2

The output is a single number: OPTIMAL_FREQ (minutes per bar).
Store it for all subsequent notebooks.
"""

# Example (uncomment on terminal):
#
# df_1min = pd.read_parquet(f'{OUTPUT_DIR}/EUSA30_Curncy_1min.parquet')
# df_1min = filter_trading_hours(df_1min)   # from nb0
#
# sig = signature_plot(df_1min)
# nv = noise_variance_by_day(df_1min)
# br = bandi_russell_optimal_freq(df_1min)
# OPTIMAL_FREQ = decide_optimal_frequency(sig, br)
#
# # Save for downstream notebooks
# pd.Series({'optimal_freq': OPTIMAL_FREQ}).to_json(f'{OUTPUT_DIR}/config.json')

print("Notebook 1 loaded. Run signature_plot() on your 1-minute data.")
