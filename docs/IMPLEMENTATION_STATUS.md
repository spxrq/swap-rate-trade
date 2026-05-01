# Implementation Status

## Milestones

- [x] Repo scaffold, docs, packaging, pre-commit hook
- [x] Thesis clarified: intraday single-tenor mean-reversion on a constant level (EUR 50Y IRS), delayed-close execution strategy
- [x] DataFrame contract revised for intraday single-tenor level-space shape
- [x] First DGP trio scaffolded: `want/ou_with_noise`, `dont_want/random_walk_with_noise`, `dont_want/ou_no_noise`
- [x] Tests for each DGP: contract conformance + claimed statistical property
- [x] DGP design notebook: `00_dgp_design.ipynb` (synthetic-design reference, not live handoff)
- [x] Layer-1 notebook implemented: `01_granularity_selection.ipynb` (prototype/reference for the snippet workflow)
- [x] Literature-grounded starter parameter values for the `want/ou_with_noise` DGP (see `PARAMETER_SOURCES.md`)
- [x] Monte Carlo validation principle locked in (ARCHITECTURE.md, DGP_CATALOG.md). Tests rewritten as power / FPR assertions at N=500, α=0.05, β=0.9, FPR-tolerance=1.5·α
- [x] DataFrame-contract session length normalised to half-open `[08:00, 17:00)` = 540 bars
- [x] Fail-fast timezone validation in all three DGPs
- [x] Layer-1 prototype: fill in RV/BV methodology (operator-led econometrics)
- [x] Public bQuant paste protocol and safe operator-readout workflow
- [x] Paste-ready bQuant snippets for data audit and Layer-1 Path-B granularity diagnostics
- [ ] Layer-2 mean-reversion snippet skeleton and methodology
- [ ] Trading-rule snippet or notebook prototype (anchor decision locked before live handoff)

## Current focus

Scaffold, parameters, Monte Carlo validation principle, and Layer-1 prototype notebooks are in place. The canonical public handoff is now `bquant_snippets/`: methodology code stays public, bQuant supplies `df`, and colleagues read back compact aggregate diagnostics instead of moving raw bank data into the repo.

Next: harden `bquant_snippets/01_granularity_pathb.py` as the live bQuant iteration capsule. Keep `notebooks/00_dgp_design.ipynb` and `notebooks/01_granularity_selection.ipynb` as non-canonical development references. Do not revive the old combined `notebooks/00_granularity_selection.ipynb`.

## Blocked / open questions

- **bQuant library allowlist** not confirmed — see `BQUANT_COMPAT.md`.
- **R availability** in bQuant unknown.
- **Missing-value convention** for real bQuant data — defer until Phase 2.
- **Anchor choice** for the trading rule (open-of-session recommended as baseline; locked before live trading-rule handoff).
- **Parameter sensitivity** — none of the starter values is better than ±2×. Document downstream sensitivity once the RV/BV methodology is in place.
- **Signature-plot Monte Carlo test for `dont_want/ou_no_noise`** — current single-path autocorrelation smoke test is a weak proxy. Layer-1 now shows this DGP is not a clean flat-signature null under level-space non-overlapping RV because OU mean reversion itself can make RV decline with Δ. Decide whether to replace this null with a no-noise martingale benchmark or normalise against the expected no-noise OU curve before writing a Monte Carlo type-I test.
- **Candle grid resolution** — `{5, 15, 30, 60, 120}` min cannot resolve a break at exactly 10 min. Decide in the Layer-1 methodology session whether to add a 10-min diagnostic point to the snippet.
- **Resampling convention** — whether each Δ-minute candle carries last-in-bin, mean, or log-return sum. Decide in the Layer-1 methodology session and document in `DATA_CONTRACT.md`.
- **OU initialisation** — both OU DGPs start at `X₀ = μ`, not from the stationary distribution. Suppresses early-session dispersion. Revisit if modelling opening dislocations matters.
- **MC test runtime** — the `adf_power` and `adf_false_positive_rate` tests run N=500 × `adfuller(autolag='AIC')` on 2000-obs series and take ~15–20 min each on this machine. Logic is correct; to speed up, switch to `maxlag=5` (skip AIC search) and/or reduce per-path `n_minutes` to ~500 — power at `theta=0.05` remains near-1 with far fewer observations.
