# Swap Execution Timing Optimization: Research Playbook

## Overview

This is a research playbook for investigating whether NWB Bank can reduce
hedging costs by systematically timing the execution of long-tenor EUR swap
hedges. It is structured as an exploratory toolkit with decision points,
not a pre-baked analysis.

## Notebook Structure

```
nb0_data_audit.py          Data availability & inventory
    |
    v
nb1_sampling_frequency.py  Optimal bar size (signature plot, Bandi-Russell)
    |
    v
nb2_eda.py                 Distribution, intraday patterns, special days
    |
    v
nb3_mean_reversion.py      Track A: formal mean reversion tests & model spec
    |
    v
nb4_impact_analysis.py     Track B: NWB-specific market impact (needs internal data)
    |
    v
nb5_simulation.py          Execution simulation & cost-benefit (Tracks A+B+C)
```

## Decision Tree

### Stage 1: Data (Notebook 0)
- **What intraday data is available on Bloomberg?**
- **What does the internal order data look like?**
- Output: data inventory, Track B feasibility assessment

### Stage 2: Sampling frequency (Notebook 1)
- Signature plot: where does RV stabilize?
- Bandi-Russell: analytical optimal frequency
- **DECISION**: Choose bar size. If never stabilizes -> tenor may be
  unsuitable for intraday analysis.

### Stage 3: EDA (Notebook 2)
- Distribution analysis -> fat tails? skewness?
  - **DECISION**: Normal / t / GED innovations for GARCH
- Intraday seasonality -> volatility varies by 2x+ across day?
  - **DECISION**: Deseasonalize before modeling, or condition on time-of-day
- Special days -> ECB / issuance / month-end behave differently?
  - **DECISION**: Exclude or treat as separate regime
- Preliminary ACF -> first hint of mean reversion?

### Stage 4: Mean reversion testing (Notebook 3, Track A)
- Test battery: VR, ADF/KPSS, Hurst, ACF
  - **IF strong evidence**: proceed to model calibration
  - **IF weak/no evidence**: Track A alone won't support a delay strategy.
    Focus shifts to Track B.
- Model specification cycle:
  1. AR(1) baseline -> half-life estimate
  2. Check residuals -> ACF structure?
     - Yes -> extend mean (ARMA)
  3. Check squared residuals -> GARCH effects?
     - Yes -> add GARCH/EGARCH
  4. Choose distribution (from EDA)
  5. Check standardized residuals -> clean?
     - Yes -> done
     - No -> iterate
- Rolling stability check -> half-life constant or regime-dependent?

### Stage 5: Impact analysis (Notebook 4, Track B)
- Requires internal order data
- **BRANCH on sample size**:
  - N >= 50: full OLS impulse response, HAC SE, controls
  - 15 <= N < 50: parsimonious OLS, bootstrap CI
  - N < 15: descriptive event study only
- Counterfactual: compare event days to non-event days
- Impact decomposition: temporary vs permanent
- **KEY OUTPUT**: what fraction of NWB's impact reverts, and how fast?

### Stage 6: Strategy simulation (Notebook 5, Tracks A+B+C)
- Only runs if Track A and/or B showed positive results
- Strategies: full delay, split execution, optimal window
- Track C extensions (conditional on vol, time-of-day)
- Cost-benefit: EUR savings, confidence intervals, risk metrics
- **FINAL OUTPUT**: recommended strategy with business case

## Dependencies

```
pip install numpy pandas matplotlib seaborn scipy statsmodels arch
```

Bloomberg: xbbg or blpapi (for data pull in Notebook 0)

## Key Assumptions to Document

1. Issuance hedges are the primary market-moving flow (testable via Track B)
2. NWB is a price-taker in the swap market (plausible given OTC bilateral)
3. Counterparties don't systematically front-run delayed execution
4. IRRBB regulatory framework allows short execution delays if risk-controlled

## What Each Outcome Means

| Track A | Track B | Implication |
|---------|---------|-------------|
| MR exists | Impact reverts | Strong case: general + specific reversion |
| MR exists | No data / inconclusive | Moderate case: general reversion only |
| No MR | Impact reverts | Still viable: own-impact reversion |
| No MR | Impact does not revert | No case for delay strategy |
