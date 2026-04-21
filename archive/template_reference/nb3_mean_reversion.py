"""
================================================================================
NOTEBOOK 3: MEAN REVERSION TESTING & MODEL SPECIFICATION (TRACK A)
================================================================================
Purpose:
    Formally test for mean reversion and calibrate the best model
    through an iterative diagnostic cycle.

    This is the core of the research. The output is:
        - Whether mean reversion exists (yes/no with statistical evidence)
        - The half-life of mean reversion (with confidence interval)
        - A properly specified model with clean residuals

Prerequisite:
    Notebook 2 complete. You know:
        - Whether to use fat-tailed distributions
        - Whether to deseasonalize
        - Whether GARCH effects are expected

Model specification cycle:
    3a: AR(1) baseline -> estimate half-life
    3b: Check residuals -> ACF, squared ACF
    3c: If residual ACF has structure -> extend mean (ARMA)
    3d: If squared residual ACF has structure -> add GARCH/EGARCH
    3e: Choose innovation distribution (normal / t / GED)
    3f: Check standardized residuals -> if clean, stop. If not, iterate.

The cycle stops when standardized residuals pass all diagnostics.
================================================================================
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
from scipy.optimize import minimize
from statsmodels.tsa.stattools import adfuller, kpss
from statsmodels.stats.diagnostic import acorr_ljungbox
from arch import arch_model
import json
import os
import warnings
warnings.filterwarnings('ignore')

OUTPUT_DIR = './swap_research'


# =============================================================================
# STEP 3a: FORMAL MEAN REVERSION TESTS
# =============================================================================
"""
Before fitting any model, test whether mean reversion exists at all.
Multiple tests provide robustness: each has different assumptions and power.
"""

def test_adf_kpss(series, name="rate levels"):
    """
    ADF and KPSS tests, used jointly for clearer inference.

    Joint interpretation:
        ADF rejects + KPSS does not reject -> stationary (mean-reverting)
        ADF does not reject + KPSS rejects -> unit root (no mean reversion)
        Both reject -> trend-stationary
        Neither rejects -> inconclusive (low power)

    Apply to:
        - Rate LEVELS within each day (tests intraday mean reversion)
        - Rate CHANGES (should be stationary; if not, something is wrong)
    """
    print(f"\n  ADF & KPSS: {name}")

    adf_stat, adf_p, adf_lags, _, adf_crit, _ = adfuller(series, autolag='AIC')
    kpss_stat, kpss_p, _, kpss_crit = kpss(series, regression='c', nlags='auto')

    print(f"    ADF: stat={adf_stat:.4f}, p={adf_p:.4f}, lags={adf_lags}")
    print(f"    KPSS: stat={kpss_stat:.4f}, p={kpss_p:.4f}")

    if adf_p < 0.05 and kpss_p >= 0.05:
        verdict = "STATIONARY (mean-reverting)"
    elif adf_p >= 0.05 and kpss_p < 0.05:
        verdict = "UNIT ROOT (no mean reversion)"
    elif adf_p < 0.05 and kpss_p < 0.05:
        verdict = "TREND-STATIONARY (ambiguous for mean reversion)"
    else:
        verdict = "INCONCLUSIVE (low power)"

    print(f"    -> {verdict}")
    return {'adf_p': adf_p, 'kpss_p': kpss_p, 'verdict': verdict}


def variance_ratio_test(returns, periods=None):
    """
    Lo-MacKinlay (1988) variance ratio test with heteroskedasticity-robust
    z-statistic.

    Under random walk: VR(k) = 1
    VR(k) < 1 -> mean reversion at horizon k
    VR(k) > 1 -> momentum at horizon k

    This is the most powerful test for our purpose because it directly
    tests at the horizons we care about (1-8 hours).
    """
    if periods is None:
        periods = [2, 4, 6, 8, 12, 16, 24, 36, 48]

    T = len(returns)
    var_1 = np.var(returns, ddof=1)
    results = []

    for k in periods:
        if k >= T // 3:
            continue

        # k-period overlapping returns
        k_ret = pd.Series(returns).rolling(k).sum().dropna().values
        var_k = np.var(k_ret, ddof=1)
        vr = var_k / (k * var_1)

        # Heteroskedasticity-robust standard error (Lo-MacKinlay)
        delta_sum = 0
        for j in range(1, k):
            weight = (2 * (k - j) / k) ** 2
            num = np.sum((returns[j:] ** 2) * (returns[:-j] ** 2))
            den = (np.sum(returns ** 2)) ** 2
            delta_j = T * num / den
            delta_sum += weight * delta_j

        z = (vr - 1) / np.sqrt(delta_sum) if delta_sum > 0 else np.nan
        p = 2 * (1 - stats.norm.cdf(abs(z))) if not np.isnan(z) else np.nan

        results.append({
            'horizon_bars': k,
            'variance_ratio': vr,
            'z_robust': z,
            'p_value': p,
        })

    res = pd.DataFrame(results)

    print(f"\nVariance Ratio Test (Lo-MacKinlay, heteroskedasticity-robust):")
    print(f"{'Horizon':>8} {'VR(k)':>8} {'z-stat':>8} {'p-value':>8} {'Signal':>15}")
    for _, row in res.iterrows():
        signal = 'MEAN REVERSION' if row['variance_ratio'] < 1 and row['p_value'] < 0.05 else \
                 'momentum' if row['variance_ratio'] > 1 and row['p_value'] < 0.05 else \
                 'inconclusive'
        print(f"{row['horizon_bars']:>8.0f} {row['variance_ratio']:>8.4f} "
              f"{row['z_robust']:>8.3f} {row['p_value']:>8.4f} {signal:>15}")

    return res


def wright_rank_vr_test(returns, periods=None):
    """
    Wright (2000) rank-based variance ratio test.
    More robust than Lo-MacKinlay when returns are non-normal (fat tails).
    Use this as a robustness check alongside the standard VR test.
    """
    if periods is None:
        periods = [2, 4, 8, 12, 24, 48]

    T = len(returns)
    ranks = stats.rankdata(returns)
    r_std = (ranks - (T + 1) / 2) / np.sqrt((T**2 - 1) / 12)

    results = []
    var_1 = np.var(r_std, ddof=0)

    for k in periods:
        if k >= T // 3:
            continue
        k_sums = pd.Series(r_std).rolling(k).sum().dropna().values
        var_k = np.var(k_sums, ddof=0)
        vr = var_k / (k * var_1)
        std_vr = np.sqrt(2 * (2*k - 1) * (k - 1) / (3 * k * T))
        z = (vr - 1) / std_vr
        p = 2 * (1 - stats.norm.cdf(abs(z)))

        results.append({
            'horizon_bars': k,
            'vr_rank': vr,
            'z_stat': z,
            'p_value': p,
        })

    return pd.DataFrame(results)


def hurst_exponent(returns, max_lag=100):
    """
    Hurst exponent via rescaled range (R/S).
    H < 0.5: mean-reverting
    H = 0.5: random walk
    H > 0.5: trending

    Less powerful than VR tests but provides a single summary number.
    Useful for communication with non-technical stakeholders.
    """
    lags = range(2, min(max_lag + 1, len(returns) // 5))
    rs_values = []

    for lag in lags:
        n_blocks = len(returns) // lag
        if n_blocks < 3:
            continue
        rs_block = []
        for i in range(n_blocks):
            block = returns[i*lag:(i+1)*lag]
            cumdev = np.cumsum(block - np.mean(block))
            R = np.max(cumdev) - np.min(cumdev)
            S = np.std(block, ddof=1)
            if S > 0:
                rs_block.append(R / S)
        if rs_block:
            rs_values.append((lag, np.mean(rs_block)))

    if len(rs_values) < 5:
        print("Insufficient data for Hurst estimation.")
        return None

    log_lags = np.log([x[0] for x in rs_values])
    log_rs = np.log([x[1] for x in rs_values])
    slope, intercept, r_val, p_val, se = stats.linregress(log_lags, log_rs)

    print(f"\nHurst Exponent: {slope:.4f} ± {se:.4f} (R²={r_val**2:.3f})")
    if slope < 0.45:
        print(f"  -> Mean-reverting")
    elif slope < 0.55:
        print(f"  -> Approximately random walk")
    else:
        print(f"  -> Trending")

    return slope


def run_all_mean_reversion_tests(prices, returns):
    """
    Run the full battery of mean reversion tests. Summarize.

    Convention: we test on RETURNS (rate changes) for ACF-based tests,
    and on LEVELS for the ADF/KPSS and OU-related tests.
    """
    print(f"\n{'='*60}")
    print(f"MEAN REVERSION TEST BATTERY")
    print(f"{'='*60}")

    # ADF/KPSS on intraday levels (pooled across days)
    # Note: pooling across days is problematic because the overnight gap
    # breaks continuity. Better to test within-day or on demeaned levels.
    print("\n--- Unit root tests (within-day levels, first 5 days shown) ---")
    daily_groups = prices.groupby(prices.index.date)
    verdicts = []
    for i, (date, group) in enumerate(daily_groups):
        if len(group) < 20:
            continue
        # Demean within day
        demeaned = group.values - group.values.mean()
        result = test_adf_kpss(demeaned, f"Intraday levels {date}")
        verdicts.append(result['verdict'])
        if i >= 4:
            break

    print(f"\n  Summary across tested days:")
    for v in set(verdicts):
        print(f"    {v}: {verdicts.count(v)} days")

    # Variance ratio tests on returns
    print("\n--- Variance ratio tests ---")
    vr = variance_ratio_test(returns.values)
    vr_rank = wright_rank_vr_test(returns.values)

    # Hurst exponent
    H = hurst_exponent(returns.values)

    # Overall assessment
    print(f"\n{'='*60}")
    print(f"OVERALL ASSESSMENT")
    print(f"{'='*60}")

    n_vr_mr = (vr['variance_ratio'] < 1).sum()
    n_vr_sig = ((vr['variance_ratio'] < 1) & (vr['p_value'] < 0.05)).sum()

    if n_vr_sig >= 2 and (H is not None and H < 0.5):
        print("STRONG evidence of mean reversion.")
        print("-> Proceed to model calibration (Step 3b-3f)")
    elif n_vr_sig >= 1 or (H is not None and H < 0.48):
        print("MODERATE evidence of mean reversion.")
        print("-> Proceed cautiously. Results may be tenor/period specific.")
    else:
        print("WEAK or NO evidence of mean reversion.")
        print("-> Track A alone may not support a delay strategy.")
        print("-> Focus shifts to Track B (bank-specific impact).")
        print("   Mean reversion in the general rate is not required if")
        print("   NWB's own impact is temporary and reverts.")

    return {
        'vr_results': vr,
        'vr_rank_results': vr_rank,
        'hurst': H,
        'intraday_verdicts': verdicts,
    }


# =============================================================================
# STEP 3b-3f: MODEL SPECIFICATION CYCLE
# =============================================================================

def fit_ar1_baseline(prices, dt=1.0):
    """
    Step 3b: Fit AR(1) on rate levels.

    r_t = c + phi * r_{t-1} + eps_t

    This is the discrete-time OU model.
    phi < 1 -> mean reversion, half-life = -ln(2) / ln(phi)

    Returns residuals for diagnostic checking.
    """
    y = prices.values[1:]
    x = prices.values[:-1]

    X = np.column_stack([np.ones(len(x)), x])
    beta = np.linalg.lstsq(X, y, rcond=None)[0]
    c, phi = beta

    residuals = y - X @ beta
    ss_res = np.sum(residuals ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r_sq = 1 - ss_res / ss_tot

    n = len(y)
    mse = ss_res / (n - 2)
    se = np.sqrt(mse * np.linalg.inv(X.T @ X).diagonal())
    t_stat = beta / se
    p_val = 2 * (1 - stats.t.cdf(np.abs(t_stat), n - 2))

    half_life = -np.log(2) / np.log(phi) if 0 < phi < 1 else np.inf

    print(f"\n{'='*60}")
    print(f"AR(1) BASELINE MODEL")
    print(f"{'='*60}")
    print(f"  r_t = {c:.6f} + {phi:.6f} * r_{{t-1}} + eps_t")
    print(f"\n  phi:       {phi:.6f} (SE: {se[1]:.6f}, t: {t_stat[1]:.2f}, "
          f"p: {p_val[1]:.4f})")
    print(f"  R²:        {r_sq:.6f}")
    print(f"  Half-life: {half_life:.1f} bars")
    print(f"  Residual std: {np.std(residuals):.6f}")

    if phi >= 1:
        print(f"\n  WARNING: phi >= 1, no mean reversion in this specification.")
        print(f"  This could mean:")
        print(f"    - No intraday mean reversion exists (Track A negative)")
        print(f"    - The model is misspecified (try ARMA or within-day only)")
        print(f"    - Overnight gaps are distorting the estimate")
        print(f"  TRY: Estimate within-day only (exclude overnight returns)")

    return {
        'c': c, 'phi': phi, 'se_phi': se[1], 'p_phi': p_val[1],
        'half_life': half_life, 'r_squared': r_sq,
        'residuals': residuals,
    }


def check_residuals(residuals, name="AR(1) residuals"):
    """
    Step 3c/3d: Diagnostic checks on model residuals.

    This function tells you what to do next:
        - ACF of residuals has structure -> extend mean equation (ARMA)
        - ACF of squared residuals has structure -> add GARCH
        - Both -> add both
        - Neither -> model is adequate, stop

    Returns a recommendation dict.
    """
    n = len(residuals)
    se = 1 / np.sqrt(n)

    # ACF of residuals
    max_lag = min(30, n // 10)
    acf_r = np.array([np.corrcoef(residuals[lag:], residuals[:-lag])[0, 1]
                       for lag in range(1, max_lag + 1)])

    # ACF of squared residuals
    acf_sq = np.array([np.corrcoef(residuals[lag:]**2, residuals[:-lag]**2)[0, 1]
                        for lag in range(1, max_lag + 1)])

    # Ljung-Box tests
    lb_r = acorr_ljungbox(residuals, lags=[6, 12, 24], return_df=True)
    lb_sq = acorr_ljungbox(residuals**2, lags=[6, 12, 24], return_df=True)

    mean_issue = any(lb_r['lb_pvalue'] < 0.05)
    var_issue = any(lb_sq['lb_pvalue'] < 0.05)

    print(f"\n{'='*60}")
    print(f"RESIDUAL DIAGNOSTICS: {name}")
    print(f"{'='*60}")

    print(f"\n  Ljung-Box on residuals (mean equation adequacy):")
    print(f"  {lb_r.to_string()}")

    print(f"\n  Ljung-Box on squared residuals (variance equation adequacy):")
    print(f"  {lb_sq.to_string()}")

    # Recommendations
    print(f"\n  DIAGNOSIS:")
    if not mean_issue and not var_issue:
        print(f"  -> Residuals are CLEAN. Model is adequate.")
        print(f"     No further specification needed. Proceed to validation.")
        recommendation = 'adequate'
    elif mean_issue and not var_issue:
        print(f"  -> Residual ACF has structure. EXTEND MEAN EQUATION.")
        print(f"     Try ARMA(p,q) with mean reversion constraint.")
        print(f"     Use AIC/BIC to select order (Step 3c).")
        recommendation = 'extend_mean'
    elif not mean_issue and var_issue:
        print(f"  -> Squared residual ACF has structure. ADD GARCH.")
        print(f"     Try GARCH(1,1) first, then EGARCH if needed.")
        print(f"     Use t-distribution if EDA showed fat tails (Step 3d).")
        recommendation = 'add_garch'
    else:
        print(f"  -> Both mean and variance equations need work.")
        print(f"     Fit ARMA-GARCH jointly (Step 3c + 3d together).")
        recommendation = 'extend_both'

    # Plot
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    axes[0, 0].bar(range(1, max_lag+1), acf_r, color='#2c3e50', alpha=0.7)
    axes[0, 0].axhline(y=1.96*se, ls='--', color='grey')
    axes[0, 0].axhline(y=-1.96*se, ls='--', color='grey')
    axes[0, 0].set_title(f'Residual ACF')

    axes[0, 1].bar(range(1, max_lag+1), acf_sq, color='#c0392b', alpha=0.7)
    axes[0, 1].axhline(y=1.96*se, ls='--', color='grey')
    axes[0, 1].axhline(y=-1.96*se, ls='--', color='grey')
    axes[0, 1].set_title(f'Squared Residual ACF')

    axes[1, 0].hist(residuals, bins=60, density=True, color='#2c3e50', alpha=0.7)
    x_range = np.linspace(residuals.min(), residuals.max(), 200)
    axes[1, 0].plot(x_range, stats.norm.pdf(x_range, 0, residuals.std()),
                    'r-', linewidth=2)
    axes[1, 0].set_title('Residual Distribution')

    stats.probplot(residuals, plot=axes[1, 1])
    axes[1, 1].set_title('QQ Plot')

    plt.suptitle(f'Diagnostics: {name}', fontsize=13, fontweight='bold')
    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/nb3_diagnostics_{name.replace(" ", "_")}.png',
                dpi=150, bbox_inches='tight')
    plt.show()

    return recommendation


def fit_arma_garch(returns, ar_order=1, ma_order=0, vol='GARCH',
                   garch_p=1, garch_q=1, dist='t'):
    """
    Steps 3c-3e: Fit ARMA(p,q)-GARCH/EGARCH(p,q) with chosen distribution.

    The mean reversion parameter lives in the AR coefficients.
    For AR(1): phi < 0 on RETURNS means mean reversion in LEVELS.

    Parameters
    ----------
    returns   : return series (rate changes, not levels)
    ar_order  : AR order in mean equation
    ma_order  : MA order in mean equation
    vol       : 'GARCH', 'EGARCH', or 'Constant' (no GARCH)
    garch_p   : GARCH p order
    garch_q   : GARCH q order
    dist      : 'normal', 't', 'ged', 'skewt'

    Returns fitted model and standardized residuals.
    """
    # Scale returns for numerical stability (arch package works better with
    # returns scaled to percentage-like magnitudes)
    scale = returns.std()
    scaled = returns / scale * 100

    model = arch_model(
        scaled,
        mean='ARX' if ar_order > 0 else 'Zero',
        lags=ar_order,
        vol=vol if vol != 'Constant' else 'ARCH',  # Use ARCH(0) for constant
        p=garch_p if vol != 'Constant' else 0,
        q=garch_q if vol != 'Constant' else 0,
        dist=dist,
    )

    result = model.fit(disp='off', options={'maxiter': 5000})

    print(f"\n{'='*60}")
    print(f"ARMA({ar_order},{ma_order})-{vol}({garch_p},{garch_q}) [{dist}]")
    print(f"{'='*60}")
    print(result.summary().tables[0])
    print(result.summary().tables[1])

    # Extract mean reversion info from AR coefficient
    ar_params = [result.params.get(f'y[{i}]', 0) for i in range(1, ar_order + 1)]
    if ar_params:
        print(f"\n  AR coefficients: {ar_params}")
        if ar_order == 1 and ar_params[0] < 0:
            # Negative AR(1) on returns -> mean reversion in levels
            phi_levels = 1 + ar_params[0]  # phi_level = 1 + ar_coef_on_returns
            hl = -np.log(2) / np.log(abs(phi_levels)) if 0 < phi_levels < 1 else np.inf
            print(f"  Implied phi on levels: {phi_levels:.4f}")
            print(f"  Implied half-life: {hl:.1f} bars")

    # Information criteria for model comparison
    print(f"\n  AIC: {result.aic:.2f}")
    print(f"  BIC: {result.bic:.2f}")

    # Standardized residuals
    std_resid = result.std_resid

    return result, std_resid


def check_standardized_residuals(std_resid, name="standardized residuals"):
    """
    Step 3f: Final diagnostic on standardized residuals.

    If these are clean, the model specification cycle is complete.
    If not, iterate (go back to 3c/3d with different orders).
    """
    print(f"\n{'='*60}")
    print(f"STANDARDIZED RESIDUAL CHECK: {name}")
    print(f"{'='*60}")

    recommendation = check_residuals(std_resid, name)

    if recommendation == 'adequate':
        print(f"\n  MODEL SPECIFICATION COMPLETE.")
        print(f"  Standardized residuals are clean.")
        print(f"  Proceed to Notebook 4 (validation) or Notebook 5 (simulation).")
    else:
        print(f"\n  MODEL NOT YET ADEQUATE. Iterate:")
        if recommendation == 'extend_mean':
            print(f"  -> Try higher AR/MA order")
        elif recommendation == 'add_garch':
            print(f"  -> Try different GARCH variant (EGARCH, GJR-GARCH)")
            print(f"     or higher GARCH order")
        elif recommendation == 'extend_both':
            print(f"  -> Increase both mean and variance complexity")
        print(f"  Then re-run check_standardized_residuals().")

    return recommendation


# =============================================================================
# TOOL: MODEL COMPARISON
# =============================================================================

def compare_models(returns, specifications=None):
    """
    Fit multiple model specifications and compare via AIC/BIC.

    Default specifications cover the most common cases.
    Add or modify based on what the diagnostics suggest.
    """
    if specifications is None:
        specifications = [
            {'ar': 1, 'ma': 0, 'vol': 'Constant', 'p': 0, 'q': 0, 'dist': 'normal'},
            {'ar': 1, 'ma': 0, 'vol': 'GARCH',    'p': 1, 'q': 1, 'dist': 'normal'},
            {'ar': 1, 'ma': 0, 'vol': 'GARCH',    'p': 1, 'q': 1, 'dist': 't'},
            {'ar': 1, 'ma': 0, 'vol': 'EGARCH',   'p': 1, 'q': 1, 'dist': 't'},
            {'ar': 1, 'ma': 1, 'vol': 'GARCH',    'p': 1, 'q': 1, 'dist': 't'},
            {'ar': 1, 'ma': 1, 'vol': 'EGARCH',   'p': 1, 'q': 1, 'dist': 't'},
            {'ar': 2, 'ma': 0, 'vol': 'GARCH',    'p': 1, 'q': 1, 'dist': 't'},
            {'ar': 2, 'ma': 0, 'vol': 'EGARCH',   'p': 1, 'q': 1, 'dist': 't'},
        ]

    results = []
    for spec in specifications:
        label = (f"AR({spec['ar']})"
                 f"{f',MA({spec[\"ma\"]})' if spec['ma'] > 0 else ''}"
                 f"-{spec['vol']}({spec['p']},{spec['q']})"
                 f" [{spec['dist']}]")
        try:
            result, std_r = fit_arma_garch(
                returns,
                ar_order=spec['ar'], ma_order=spec['ma'],
                vol=spec['vol'], garch_p=spec['p'], garch_q=spec['q'],
                dist=spec['dist'],
            )
            # Quick residual check
            lb = acorr_ljungbox(std_r, lags=[12], return_df=True)
            lb_sq = acorr_ljungbox(std_r**2, lags=[12], return_df=True)

            results.append({
                'specification': label,
                'aic': result.aic,
                'bic': result.bic,
                'log_lik': result.loglikelihood,
                'lb_resid_p': lb['lb_pvalue'].values[0],
                'lb_sq_resid_p': lb_sq['lb_pvalue'].values[0],
                'resid_clean': lb['lb_pvalue'].values[0] > 0.05,
                'sq_resid_clean': lb_sq['lb_pvalue'].values[0] > 0.05,
                'both_clean': (lb['lb_pvalue'].values[0] > 0.05 and
                              lb_sq['lb_pvalue'].values[0] > 0.05),
            })
        except Exception as e:
            print(f"  Failed: {label} ({e})")

    comp = pd.DataFrame(results)
    comp = comp.sort_values('bic')

    print(f"\n{'='*60}")
    print(f"MODEL COMPARISON (sorted by BIC)")
    print(f"{'='*60}")
    print(comp.to_string(index=False, float_format='%.2f'))

    # Recommendation
    clean_models = comp[comp['both_clean']]
    if len(clean_models) > 0:
        best = clean_models.iloc[0]
        print(f"\n  RECOMMENDED: {best['specification']}")
        print(f"  (Lowest BIC among models with clean residuals)")
    else:
        print(f"\n  WARNING: No specification produces fully clean residuals.")
        print(f"  Best available: {comp.iloc[0]['specification']}")
        print(f"  Consider: higher orders, different distribution, or")
        print(f"  accepting some residual structure if economically minor.")

    return comp


# =============================================================================
# TOOL: OU MAXIMUM LIKELIHOOD (alternative to ARMA-GARCH)
# =============================================================================

def ou_mle(prices, dt=1.0):
    """
    Direct MLE estimation of continuous-time OU parameters.
    
    Useful as a cross-check against the discrete AR(1) / ARMA-GARCH results.
    Gives kappa, mu, sigma directly in interpretable units.
    """
    p = np.asarray(prices, dtype=float)
    n = len(p) - 1

    def neg_ll(params):
        kappa, mu, sigma = params
        if kappa <= 0 or sigma <= 0:
            return 1e10
        ek = np.exp(-kappa * dt)
        cond_mean = mu + (p[:-1] - mu) * ek
        cond_var = (sigma**2) / (2*kappa) * (1 - np.exp(-2*kappa*dt))
        if cond_var <= 0:
            return 1e10
        resid = p[1:] - cond_mean
        return 0.5 * n * np.log(2*np.pi*cond_var) + 0.5 * np.sum(resid**2) / cond_var

    # Initialize from OLS
    y = np.diff(p)
    X = np.column_stack([np.ones(len(p)-1), p[:-1]])
    b = np.linalg.lstsq(X, y, rcond=None)[0]
    k0 = max(-b[1]/dt, 0.001)
    m0 = -b[0]/b[1] if b[1] != 0 else np.mean(p)
    s0 = max(np.std(y - X @ b) / np.sqrt(dt), 0.001)

    res = minimize(neg_ll, [k0, m0, s0], method='Nelder-Mead',
                   options={'maxiter': 10000})
    kappa, mu, sigma = res.x
    hl = np.log(2) / kappa if kappa > 0 else np.inf

    print(f"\nOU MLE Results:")
    print(f"  kappa (speed): {kappa:.6f}")
    print(f"  mu (level):    {mu:.4f}")
    print(f"  sigma (vol):   {sigma:.6f}")
    print(f"  Half-life:     {hl:.1f} bars")
    print(f"  Log-lik:       {-res.fun:.2f}")

    return {'kappa': kappa, 'mu': mu, 'sigma': sigma,
            'half_life': hl, 'log_lik': -res.fun}


# =============================================================================
# TOOL: ROLLING STABILITY CHECK
# =============================================================================

def rolling_half_life(prices, window=500):
    """
    Estimate half-life in rolling windows to check stability.

    If the half-life is stable: unconditional strategy is fine.
    If it varies a lot: you need regime conditioning (Track C extension).
    """
    p = prices.values
    records = []

    for i in range(window, len(p)):
        w = p[i-window:i]
        y = np.diff(w)
        x = w[:-1]
        X = np.column_stack([np.ones(len(x)), x])
        b = np.linalg.lstsq(X, y, rcond=None)[0]
        phi = 1 + b[1]  # b[1] is the slope on levels in the diff regression
        hl = -np.log(2) / np.log(phi) if 0 < phi < 1 else np.nan
        records.append({'index': i, 'phi': phi, 'half_life': hl})

    roll = pd.DataFrame(records)

    fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True)

    hl_clipped = roll['half_life'].clip(upper=roll['half_life'].quantile(0.95))
    axes[0].plot(roll['index'], hl_clipped, color='#1a5276', linewidth=0.8)
    axes[0].set_ylabel('Half-life (bars)')
    axes[0].set_title(f'Rolling Half-Life (window={window})')

    axes[1].plot(roll['index'], roll['phi'], color='#c0392b', linewidth=0.8)
    axes[1].axhline(y=1, ls='--', color='grey')
    axes[1].set_ylabel('phi (AR coefficient on levels)')
    axes[1].set_xlabel('Observation')

    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/nb3_rolling_halflife.png', dpi=150, bbox_inches='tight')
    plt.show()

    hl_valid = roll['half_life'].dropna()
    print(f"\nRolling Half-Life Summary:")
    print(f"  Median: {hl_valid.median():.1f} bars")
    print(f"  IQR:    [{hl_valid.quantile(0.25):.1f}, {hl_valid.quantile(0.75):.1f}]")
    print(f"  Pct windows with phi < 1: {(roll['phi'] < 1).mean()*100:.1f}%")

    if (roll['phi'] < 1).mean() < 0.6:
        print("  WARNING: Mean reversion not present in >40% of windows.")
        print("  The signal is regime-dependent. Track C conditioning may help.")

    return roll


# =============================================================================
# EXECUTION
# =============================================================================
"""
Workflow:
    1. Load returns from Notebook 2
    2. run_all_mean_reversion_tests() -> overall assessment
    3. IF positive: fit_ar1_baseline() -> first half-life estimate
    4. check_residuals() -> get recommendation
    5. Follow recommendation:
       - 'adequate': done, go to validation
       - 'extend_mean': try ARMA orders
       - 'add_garch': try GARCH/EGARCH
       - 'extend_both': try ARMA-GARCH jointly
    6. fit_arma_garch() with chosen specification
    7. check_standardized_residuals() -> if clean, done. If not, iterate.
    8. compare_models() for systematic selection
    9. rolling_half_life() to check stability
    10. ou_mle() as cross-check

Save final model specification and half-life estimate for Notebook 5.
"""

# Example (uncomment):
#
# prices, returns = load_resampled_data('EUSA30_Curncy', freq=5)
#
# # Step 1: Test battery
# test_results = run_all_mean_reversion_tests(prices, returns)
#
# # Step 2: Baseline model
# ar1 = fit_ar1_baseline(prices)
#
# # Step 3: Check residuals
# rec = check_residuals(ar1['residuals'])
#
# # Step 4: Follow recommendation (example: add GARCH with t-dist)
# # result, std_r = fit_arma_garch(returns, ar_order=1, vol='EGARCH', dist='t')
# # final_rec = check_standardized_residuals(std_r)
#
# # Step 5: Systematic comparison
# # comp = compare_models(returns)
#
# # Step 6: Stability
# # roll = rolling_half_life(prices)
#
# # Step 7: Cross-check
# # ou = ou_mle(prices.values)

print("Notebook 3 loaded. Start with run_all_mean_reversion_tests().")
