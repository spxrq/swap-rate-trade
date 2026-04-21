# Implementation Status

## Milestones

- [x] Repo scaffold, docs, packaging, pre-commit hook
- [x] Thesis clarified: intraday single-tenor mean-reversion on a constant level (EUR 50Y IRS), delayed-close execution strategy
- [x] DataFrame contract revised for intraday single-tenor level-space shape
- [x] First DGP trio scaffolded: `want/ou_with_noise`, `dont_want/random_walk_with_noise`, `dont_want/ou_no_noise`
- [x] Tests for each DGP: contract conformance + claimed statistical property
- [x] Layer-1 notebook skeleton: `00_granularity_selection.ipynb` (cells labelled, methodology cells empty)
- [x] Literature-grounded starter parameter values for the `want/ou_with_noise` DGP (see `PARAMETER_SOURCES.md`)
- [x] Monte Carlo validation principle locked in (CLAUDE.md, ARCHITECTURE.md, DGP_CATALOG.md). Tests rewritten as power / FPR assertions at N=500, α=0.05, β=0.9, FPR-tolerance=1.5·α
- [x] DataFrame-contract session length normalised to half-open `[08:00, 17:00)` = 540 bars
- [x] Fail-fast timezone validation in all three DGPs
- [ ] Layer-1 notebook: fill in RV/BV methodology (operator-led econometrics)
- [ ] Layer-2 mean-reversion notebook skeleton and methodology
- [ ] Trading-rule notebook (anchor decision locked in here)

## Current focus

Scaffold and parameters are in place. The `want/ou_with_noise` DGP can now be simulated end-to-end. Next: fill in the RV/BV methodology cells in `notebooks/00_granularity_selection.ipynb` (operator-led econometrics).

## Blocked / open questions

- **bQuant library allowlist** not confirmed — see `BQUANT_COMPAT.md`.
- **R availability** in bQuant unknown.
- **Missing-value convention** for real bQuant data — defer until Phase 2.
- **Anchor choice** for the trading rule (open-of-session recommended as baseline; locked in at trading-rule notebook stage).
- **Parameter sensitivity** — none of the starter values is better than ±2×. Document downstream sensitivity once the RV/BV methodology is in place.
- **Signature-plot Monte Carlo test for `dont_want/ou_no_noise`** — current single-path autocorrelation smoke test is a weak proxy. Replace with a proper RV/BV signature-plot flatness statistic under a Monte Carlo type-I criterion once Layer-1 methodology is in place.
- **Candle grid resolution** — `{5, 15, 30, 60, 120}` min cannot resolve a break at exactly 10 min. Decide in the Layer-1 methodology session whether to add a 10-min diagnostic point.
- **Resampling convention** — whether each Δ-minute candle carries last-in-bin, mean, or log-return sum. Decide in the Layer-1 methodology session and document in `DATA_CONTRACT.md`.
- **OU initialisation** — both OU DGPs start at `X₀ = μ`, not from the stationary distribution. Suppresses early-session dispersion. Revisit if modelling opening dislocations matters.
- **MC test runtime** — the `adf_power` and `adf_false_positive_rate` tests run N=500 × `adfuller(autolag='AIC')` on 2000-obs series and take ~15–20 min each on this machine. Logic is correct; to speed up, switch to `maxlag=5` (skip AIC search) and/or reduce per-path `n_minutes` to ~500 — power at `theta=0.05` remains near-1 with far fewer observations.
