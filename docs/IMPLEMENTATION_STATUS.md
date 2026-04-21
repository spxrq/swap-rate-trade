# Implementation Status

## Milestones

- [x] Repo scaffold, docs, packaging, pre-commit hook
- [x] Thesis clarified: intraday single-tenor mean-reversion on a constant level (EUR 50Y IRS), delayed-close execution strategy
- [x] DataFrame contract revised for intraday single-tenor level-space shape
- [x] First DGP trio scaffolded: `want/ou_with_noise`, `dont_want/random_walk_with_noise`, `dont_want/ou_no_noise`
- [x] Tests for each DGP: contract conformance + claimed statistical property
- [x] Layer-1 notebook skeleton: `00_granularity_selection.ipynb` (cells labelled, methodology cells empty)
- [ ] **Realistic parameter values** for the DGPs (μ, mean-reversion half-life, σ_efficient, σ_noise)
- [ ] Layer-1 notebook: fill in RV/BV methodology (operator-led econometrics)
- [ ] Layer-2 mean-reversion notebook skeleton and methodology
- [ ] Trading-rule notebook (anchor decision locked in here)

## Current focus

DGPs and Layer-1 notebook are scaffolded. Next session opens with parameter values for the three DGPs, then we fill in the Layer-1 notebook methodology together.

## Blocked / open questions

- **Parameter values** for a realistic 50Y EUR IRS intraday model — see above.
- **bQuant library allowlist** not confirmed — see `BQUANT_COMPAT.md`.
- **R availability** in bQuant unknown.
- **Missing-value convention** for real bQuant data — defer until Phase 2.
- **Anchor choice** for the trading rule (open-of-session recommended as baseline; locked in at trading-rule notebook stage).
