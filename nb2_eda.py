"""
================================================================================
NOTEBOOK 2: EXPLORATORY DATA ANALYSIS
================================================================================
Purpose:
    Understand the statistical properties of the data at the chosen
    sampling frequency BEFORE imposing any model structure.

    This step builds intuition and determines which model classes
    are appropriate in Notebook 3.

Prerequisite:
    Notebook 1 complete. OPTIMAL_FREQ chosen and data resampled.

Key questions answered here:
    - What does the return distribution look like? (tails, skewness)
    - Are there intraday patterns? (volatility smile, drift)
    - Are there special days that behave differently? (ECB, issuance, month-end)
    - What does the autocorrelation structure look like at first glance?

Decision outputs:
    - Whether fat-tailed distributions are needed (-> t or GED in GARCH)
    - Whether intraday seasonality must be handled (-> deseasonalize or condition)
    - Whether certain days should be excluded or treated separately
    - First indication of mean reversion (negative ACF) or lack thereof
================================================================================
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
import json
import os

OUTPUT_DIR = './swap_research'


# =============================================================================
# SETUP: LOAD DATA AT CHOSEN FREQUENCY
# =============================================================================

def load_resampled_data(ticker='EUSA30_Curncy', freq=None):
    """Load 1-min data and resample to chosen frequency."""
    if freq is None:
        config = json.load(open(f'{OUTPUT_DIR}/config.json'))
        freq = int(config['optimal_freq'])

    path = f'{OUTPUT_DIR}/{ticker}_1min.parquet'
    df = pd.read_parquet(path)

    resampled = df['close'].resample(f'{freq}min').last().dropna()
    returns = resampled.diff().dropna()

    print(f"Loaded {ticker} at {freq}-min frequency")
    print(f"  Observations: {len(resampled)}")
    print(f"  Trading days: {resampled.index.normalize().nunique()}")
    print(f"  Bars per day: ~{len(resampled) / resampled.index.normalize().nunique():.0f}")

    return resampled, returns


# =============================================================================
# TOOL: DISTRIBUTION ANALYSIS
# =============================================================================

def analyze_distribution(returns, name="returns"):
    """
    Full distribution analysis of returns.

    What to look for:
        - Excess kurtosis > 0: fat tails present, need t or GED distribution
          in GARCH specification. Normal assumption will understate risk.
        - Significant skewness: asymmetry in returns. If negative, large
          down moves are more common. Relevant for EGARCH leverage term.
        - QQ plot deviation from normal line: visual confirmation of tails.

    Decision rules:
        - Kurtosis > 3 (excess > 0): use Student-t innovations
        - Kurtosis > 6 (excess > 3): consider GED or skewed-t
        - |Skewness| > 0.5: consider asymmetric distribution or EGARCH
    """
    r = returns.values if hasattr(returns, 'values') else np.asarray(returns)

    print(f"\n{'='*60}")
    print(f"Distribution Analysis: {name}")
    print(f"{'='*60}")

    # Basic moments
    print(f"\n  N:          {len(r)}")
    print(f"  Mean:       {np.mean(r):.6f}")
    print(f"  Std:        {np.std(r):.6f}")
    print(f"  Skewness:   {stats.skew(r):.4f}")
    print(f"  Kurtosis:   {stats.kurtosis(r):.4f} (excess, normal = 0)")

    # Formal normality tests
    jb_stat, jb_p = stats.jarque_bera(r)
    sw_stat, sw_p = stats.shapiro(r[:5000])  # Shapiro limited to 5000 obs
    print(f"\n  Jarque-Bera: stat={jb_stat:.2f}, p={jb_p:.4e}")
    print(f"  Shapiro-Wilk: stat={sw_stat:.4f}, p={sw_p:.4e}")

    # Interpretation
    kurt = stats.kurtosis(r)
    skew = stats.skew(r)

    print(f"\n  INTERPRETATION:")
    if kurt > 3:
        print(f"  -> Heavy tails (excess kurtosis = {kurt:.1f}).")
        print(f"     USE: GED or skewed-t innovations in GARCH.")
    elif kurt > 0:
        print(f"  -> Moderate fat tails (excess kurtosis = {kurt:.1f}).")
        print(f"     USE: Student-t innovations in GARCH.")
    else:
        print(f"  -> Tails approximately normal. Gaussian GARCH is fine.")

    if abs(skew) > 0.5:
        print(f"  -> Notable skewness ({skew:.2f}).")
        print(f"     CONSIDER: EGARCH for leverage effects, or skewed-t.")
    else:
        print(f"  -> Approximately symmetric.")

    # Visualization
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Histogram with normal overlay
    axes[0, 0].hist(r, bins=80, density=True, color='#2c3e50', alpha=0.7,
                    edgecolor='white', linewidth=0.3)
    x = np.linspace(r.min(), r.max(), 200)
    axes[0, 0].plot(x, stats.norm.pdf(x, np.mean(r), np.std(r)),
                    'r-', linewidth=2, label='Normal')
    # Fit t-distribution for comparison
    df_t, loc_t, scale_t = stats.t.fit(r)
    axes[0, 0].plot(x, stats.t.pdf(x, df_t, loc_t, scale_t),
                    'g--', linewidth=2, label=f't (df={df_t:.1f})')
    axes[0, 0].legend()
    axes[0, 0].set_title('Return Distribution')

    # QQ plot
    stats.probplot(r, dist="norm", plot=axes[0, 1])
    axes[0, 1].set_title('QQ Plot vs Normal')
    axes[0, 1].get_lines()[0].set_color('#2c3e50')
    axes[0, 1].get_lines()[1].set_color('#c0392b')

    # Log-scale tails (reveals tail behavior better)
    sorted_abs = np.sort(np.abs(r))[::-1]
    rank = np.arange(1, len(sorted_abs) + 1) / len(sorted_abs)
    axes[1, 0].semilogy(sorted_abs[:len(sorted_abs)//4], rank[:len(rank)//4],
                        '.', color='#2c3e50', markersize=2)
    axes[1, 0].set_xlabel('|Return|')
    axes[1, 0].set_ylabel('P(|R| > x)')
    axes[1, 0].set_title('Tail Distribution (log scale)')
    axes[1, 0].grid(True, alpha=0.3)

    # Returns over time
    if hasattr(returns, 'index'):
        axes[1, 1].plot(returns.index, returns.values, color='#2c3e50',
                        linewidth=0.3, alpha=0.7)
        axes[1, 1].set_title('Returns Over Time')
        axes[1, 1].set_ylabel('Δr')
    else:
        axes[1, 1].plot(r, color='#2c3e50', linewidth=0.3, alpha=0.7)
        axes[1, 1].set_title('Returns Over Time')

    plt.suptitle(f'Distribution Diagnostics: {name}', fontsize=13, fontweight='bold')
    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/nb2_distribution.png', dpi=150, bbox_inches='tight')
    plt.show()

    return {
        'skewness': skew,
        'excess_kurtosis': kurt,
        'jb_p': jb_p,
        't_df_fit': df_t,
        'needs_fat_tails': kurt > 0,
        'needs_asymmetry': abs(skew) > 0.5,
    }


# =============================================================================
# TOOL: INTRADAY SEASONALITY
# =============================================================================

def intraday_patterns(prices, returns):
    """
    Map intraday patterns in returns, volatility, and price drift.

    What to look for:
        - U-shaped volatility: high at open and close, low midday.
          If present, raw returns mix signal with seasonality.
          You may want to deseasonalize before fitting mean reversion models.
        - Systematic drift: does the rate tend to rise in the morning
          and fall in the afternoon, or vice versa? This could be
          driven by NWB and similar banks all hedging at similar times.
        - Volume patterns (if available): when is liquidity highest?

    Decision rules:
        - If volatility varies by > 2x across the day: deseasonalize
          returns before GARCH fitting, or include time-of-day dummies
        - If systematic drift exists: this IS the signal you want to exploit,
          so document it carefully
    """
    df = pd.DataFrame({
        'price': prices,
        'return': returns,
    })
    df['hour'] = df.index.hour
    df['minute'] = df.index.minute
    df['time_decimal'] = df['hour'] + df['minute'] / 60
    df['abs_return'] = df['return'].abs()
    df['sq_return'] = df['return'] ** 2

    # Aggregate by hour
    hourly = df.groupby('hour').agg(
        mean_return=('return', 'mean'),
        std_return=('return', 'std'),
        mean_abs_return=('abs_return', 'mean'),
        median_abs_return=('abs_return', 'median'),
        n=('return', 'count'),
    )

    # Test if mean return is significantly different from zero per hour
    hourly['se'] = hourly['std_return'] / np.sqrt(hourly['n'])
    hourly['t_stat'] = hourly['mean_return'] / hourly['se']
    hourly['significant'] = hourly['t_stat'].abs() > 1.96

    print(f"\nIntraday Patterns by Hour:")
    print(hourly[['mean_return', 'se', 't_stat', 'significant',
                   'mean_abs_return', 'n']].to_string(float_format='%.6f'))

    # Volatility ratio (max/min across hours)
    vol_ratio = hourly['mean_abs_return'].max() / hourly['mean_abs_return'].min()
    print(f"\nVolatility ratio (max/min hour): {vol_ratio:.2f}")

    if vol_ratio > 2:
        print("  -> Strong intraday seasonality in volatility.")
        print("     RECOMMENDATION: deseasonalize returns before fitting GARCH,")
        print("     or include hour dummies in the variance equation.")
    elif vol_ratio > 1.5:
        print("  -> Moderate intraday seasonality.")
        print("     CONSIDER: deseasonalizing if residual diagnostics are poor.")
    else:
        print("  -> Weak intraday seasonality. Probably safe to ignore.")

    # Check for systematic drift
    sig_hours = hourly[hourly['significant']]
    if len(sig_hours) > 0:
        print(f"\n  Hours with significant mean return:")
        for h, row in sig_hours.iterrows():
            direction = "positive" if row['mean_return'] > 0 else "negative"
            print(f"    {h}:00 - {direction} drift ({row['mean_return']:.6f}, "
                  f"t={row['t_stat']:.2f})")
        print("  This drift pattern could be driven by systematic hedging demand.")
        print("  This IS relevant for the execution timing question.")

    # Visualization
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    axes[0].bar(hourly.index, hourly['mean_return'],
                color=['#27ae60' if x > 0 else '#c0392b' for x in hourly['mean_return']],
                alpha=0.7)
    axes[0].axhline(y=0, color='black', linewidth=0.5)
    # Mark significant hours
    for h, row in sig_hours.iterrows():
        axes[0].annotate('*', (h, row['mean_return']),
                         ha='center', fontsize=14, fontweight='bold')
    axes[0].set_xlabel('Hour (CET)')
    axes[0].set_ylabel('Mean return')
    axes[0].set_title('Mean Return by Hour (* = significant at 5%)')

    axes[1].bar(hourly.index, hourly['mean_abs_return'], color='#2c3e50', alpha=0.7)
    axes[1].set_xlabel('Hour (CET)')
    axes[1].set_ylabel('Mean |return|')
    axes[1].set_title('Volatility by Hour')

    # Cumulative return through the day (average)
    intraday_cum = df.groupby(df.index.time)['return'].mean().cumsum()
    axes[2].plot(range(len(intraday_cum)), intraday_cum.values,
                 color='#1a5276', linewidth=1.5)
    axes[2].axhline(y=0, color='grey', ls='--', alpha=0.5)
    axes[2].set_xlabel('Bar within day')
    axes[2].set_ylabel('Cumulative mean return')
    axes[2].set_title('Average Intraday Drift Pattern')

    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/nb2_intraday.png', dpi=150, bbox_inches='tight')
    plt.show()

    return hourly, vol_ratio


# =============================================================================
# TOOL: SPECIAL DAYS ANALYSIS
# =============================================================================

def special_days_analysis(returns, ecb_dates=None, issuance_dates=None):
    """
    Check whether certain days behave differently from the baseline.

    Types of special days:
        - ECB meeting/announcement days (higher vol, possible jumps)
        - NWB issuance days (if known from internal data)
        - Month-end / quarter-end (rebalancing flows)
        - Days with extreme moves (> 3 sigma)

    Decision rules:
        - If special days have 2x+ the volatility: consider excluding
          from mean reversion estimation, or fitting separate regime
        - If they show different autocorrelation: model may need
          regime-switching component
    """
    daily = returns.groupby(returns.index.date).agg(['mean', 'std', 'count'])
    daily.columns = ['mean_ret', 'vol', 'n_bars']
    daily.index = pd.to_datetime(daily.index)

    # Month-end
    daily['is_month_end'] = daily.index.is_month_end | (
        daily.index + pd.Timedelta(days=1)).is_month_start
    daily['is_quarter_end'] = daily.index.is_quarter_end

    # ECB dates (user provides, or leave empty)
    if ecb_dates:
        ecb_set = set(pd.to_datetime(ecb_dates).date)
        daily['is_ecb'] = daily.index.date.isin(ecb_set)  # noqa
    else:
        daily['is_ecb'] = False

    # Issuance dates
    if issuance_dates:
        iss_set = set(pd.to_datetime(issuance_dates).date)
        daily['is_issuance'] = daily.index.date.isin(iss_set)  # noqa
    else:
        daily['is_issuance'] = False

    # Extreme days (> 2 std of daily vol)
    vol_mean = daily['vol'].mean()
    vol_std = daily['vol'].std()
    daily['is_extreme'] = daily['vol'] > vol_mean + 2 * vol_std

    # Compare
    categories = {
        'All days': daily,
        'Month-end': daily[daily['is_month_end']],
        'Quarter-end': daily[daily['is_quarter_end']],
        'ECB days': daily[daily['is_ecb']],
        'Issuance days': daily[daily['is_issuance']],
        'Extreme vol days': daily[daily['is_extreme']],
        'Normal days': daily[~daily['is_month_end'] & ~daily['is_ecb']
                             & ~daily['is_issuance'] & ~daily['is_extreme']],
    }

    print(f"\nSpecial Days Comparison:")
    print(f"{'Category':<20} {'N days':>8} {'Mean vol':>12} {'Vol ratio':>12}")
    print('-' * 55)

    baseline_vol = categories['Normal days']['vol'].mean()
    for name, subset in categories.items():
        if len(subset) == 0:
            continue
        vol = subset['vol'].mean()
        ratio = vol / baseline_vol if baseline_vol > 0 else np.nan
        print(f"{name:<20} {len(subset):>8} {vol:>12.6f} {ratio:>12.2f}")

    # Decision guidance
    print(f"\n  INTERPRETATION:")
    for name in ['ECB days', 'Month-end', 'Issuance days']:
        subset = categories[name]
        if len(subset) == 0:
            continue
        ratio = subset['vol'].mean() / baseline_vol
        if ratio > 2:
            print(f"  -> {name}: volatility {ratio:.1f}x normal.")
            print(f"     CONSIDER: exclude from mean reversion estimation,")
            print(f"     or flag as separate regime.")
        elif ratio > 1.3:
            print(f"  -> {name}: somewhat elevated ({ratio:.1f}x). Monitor.")

    n_extreme = daily['is_extreme'].sum()
    pct_extreme = n_extreme / len(daily) * 100
    print(f"\n  Extreme vol days: {n_extreme} ({pct_extreme:.1f}% of sample)")
    if pct_extreme > 5:
        print("  -> More than 5% extreme days. Robust methods advisable.")

    return daily


# =============================================================================
# TOOL: PRELIMINARY AUTOCORRELATION
# =============================================================================

def preliminary_acf(returns, max_lag=60):
    """
    First look at autocorrelation structure.

    This is NOT the formal mean reversion test (that's Notebook 3).
    This is a preview to understand what kind of model might be needed.

    What to look for:
        - Negative ACF at lag 1-3: immediate mean reversion signal
        - Positive ACF at lag 1-3: momentum / microstructure noise residual
        - Slow decay in ACF: long memory, may need fractional differencing
        - Significant ACF in squared returns: GARCH effects present

    This preview shapes expectations for Notebook 3's formal testing.
    """
    r = returns.values if hasattr(returns, 'values') else np.asarray(returns)
    n = len(r)

    # Compute ACF manually (for more control than statsmodels)
    acf = np.array([np.corrcoef(r[lag:], r[:-lag])[0, 1]
                     for lag in range(1, max_lag + 1)])
    acf_sq = np.array([np.corrcoef(r[lag:]**2, r[:-lag]**2)[0, 1]
                        for lag in range(1, max_lag + 1)])

    se = 1 / np.sqrt(n)

    # Summary statistics
    print(f"\nPreliminary Autocorrelation (first 10 lags):")
    print(f"{'Lag':>5} {'ACF(r)':>10} {'ACF(r²)':>10} {'ACF(r) sig?':>12}")
    for i in range(min(10, max_lag)):
        sig = '*' if abs(acf[i]) > 1.96 * se else ''
        print(f"{i+1:>5} {acf[i]:>10.4f} {acf_sq[i]:>10.4f} {sig:>12}")

    # Quick interpretation
    n_neg_sig = sum((acf[:5] < 0) & (np.abs(acf[:5]) > 1.96 * se))
    n_pos_sig = sum((acf[:5] > 0) & (np.abs(acf[:5]) > 1.96 * se))
    n_sq_sig = sum(np.abs(acf_sq[:10]) > 1.96 * se)

    print(f"\n  PREVIEW (not a formal test, see Notebook 3):")
    if n_neg_sig > 0:
        print(f"  -> {n_neg_sig} of first 5 lags show significant negative ACF.")
        print(f"     Suggestive of mean reversion. Good sign for Track A.")
    elif n_pos_sig > 0:
        print(f"  -> {n_pos_sig} of first 5 lags show significant positive ACF.")
        print(f"     Could be residual microstructure or momentum.")
        print(f"     Check if sampling frequency should be coarser (Notebook 1).")
    else:
        print(f"  -> No significant autocorrelation in first 5 lags.")
        print(f"     Mean reversion may be weak or absent at this frequency.")

    if n_sq_sig > 2:
        print(f"  -> {n_sq_sig} of first 10 lags in squared returns are significant.")
        print(f"     GARCH effects clearly present. Notebook 3 will need")
        print(f"     a volatility model alongside the mean equation.")
    else:
        print(f"  -> Weak/no GARCH effects. Simple OU may suffice.")

    # Visualization
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    colors_r = ['#c0392b' if v < 0 else '#2980b9' for v in acf[:max_lag]]
    axes[0].bar(range(1, max_lag + 1), acf, color=colors_r, alpha=0.7, width=0.8)
    axes[0].axhline(y=1.96*se, ls='--', color='grey', alpha=0.5)
    axes[0].axhline(y=-1.96*se, ls='--', color='grey', alpha=0.5)
    axes[0].axhline(y=0, color='black', linewidth=0.5)
    axes[0].set_xlabel('Lag')
    axes[0].set_ylabel('Autocorrelation')
    axes[0].set_title('ACF of Returns (red = negative)')

    colors_sq = ['#c0392b' if abs(v) > 1.96*se else '#2c3e50' for v in acf_sq[:max_lag]]
    axes[1].bar(range(1, max_lag + 1), acf_sq, color=colors_sq, alpha=0.7, width=0.8)
    axes[1].axhline(y=1.96*se, ls='--', color='grey', alpha=0.5)
    axes[1].axhline(y=-1.96*se, ls='--', color='grey', alpha=0.5)
    axes[1].axhline(y=0, color='black', linewidth=0.5)
    axes[1].set_xlabel('Lag')
    axes[1].set_ylabel('Autocorrelation')
    axes[1].set_title('ACF of Squared Returns (red = significant)')

    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/nb2_acf_preview.png', dpi=150, bbox_inches='tight')
    plt.show()

    return {
        'acf': acf,
        'acf_sq': acf_sq,
        'suggests_mean_reversion': n_neg_sig > 0,
        'suggests_garch': n_sq_sig > 2,
    }


# =============================================================================
# TOOL: DESEASONALIZATION (conditional on intraday_patterns results)
# =============================================================================

def deseasonalize_returns(returns):
    """
    Remove intraday volatility seasonality by dividing returns
    by the average absolute return for that time of day.

    Use this if intraday_patterns() showed strong seasonality (vol ratio > 2).
    The deseasonalized returns should then be used in Notebook 3
    for cleaner mean reversion testing.

    Note: this is a simple multiplicative deseasonalization.
    More sophisticated approaches (e.g., Fourier flexible form) exist
    but this is usually sufficient.
    """
    df = pd.DataFrame({'return': returns})
    df['time'] = df.index.time

    # Compute seasonal factor: average |return| by time of day
    seasonal = df.groupby('time')['return'].apply(lambda x: x.abs().mean())
    global_mean = df['return'].abs().mean()
    seasonal_factor = seasonal / global_mean

    # Deseasonalize
    df['factor'] = df['time'].map(seasonal_factor)
    df['return_deseas'] = df['return'] / df['factor']

    print(f"\nDeseasonalization applied.")
    print(f"  Seasonal factor range: [{seasonal_factor.min():.2f}, "
          f"{seasonal_factor.max():.2f}]")
    print(f"  Original return std:       {returns.std():.6f}")
    print(f"  Deseasonalized return std: {df['return_deseas'].std():.6f}")

    return df['return_deseas']


# =============================================================================
# EXECUTION
# =============================================================================
"""
Workflow:
    1. Load resampled data
    2. analyze_distribution() -> determines tail treatment in Notebook 3
    3. intraday_patterns() -> determines if deseasonalization needed
    4. special_days_analysis() -> determines exclusions or regime flags
    5. preliminary_acf() -> sets expectations for Notebook 3
    6. If needed: deseasonalize_returns()
    7. Save EDA findings for Notebook 3

At the end of this notebook, you should know:
    - Whether to use t / GED / normal innovations
    - Whether to deseasonalize before modeling
    - Which days to exclude or treat separately
    - Whether mean reversion looks promising (preview, not confirmed)
"""

# Example (uncomment on terminal):
#
# prices, returns = load_resampled_data('EUSA30_Curncy', freq=5)
#
# dist_info = analyze_distribution(returns, 'EUSA30 5-min returns')
# hourly, vol_ratio = intraday_patterns(prices, returns)
#
# # ECB dates: add actual dates here from Bloomberg (ECB <GO>)
# ecb_dates = []  # ['2025-10-17', '2025-12-12', '2026-01-30', ...]
# daily = special_days_analysis(returns, ecb_dates=ecb_dates)
#
# acf_info = preliminary_acf(returns)
#
# # If vol_ratio > 2:
# # returns_clean = deseasonalize_returns(returns)
# # acf_info_clean = preliminary_acf(returns_clean)
#
# # Save EDA findings
# eda_findings = {
#     'needs_fat_tails': dist_info['needs_fat_tails'],
#     'needs_asymmetry': dist_info['needs_asymmetry'],
#     't_df_estimate': dist_info['t_df_fit'],
#     'vol_ratio': vol_ratio,
#     'needs_deseasonalization': vol_ratio > 2,
#     'suggests_mean_reversion': acf_info['suggests_mean_reversion'],
#     'suggests_garch': acf_info['suggests_garch'],
# }
# pd.Series(eda_findings).to_json(f'{OUTPUT_DIR}/eda_findings.json')

print("Notebook 2 loaded. Run analyze_distribution() first.")
