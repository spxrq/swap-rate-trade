# Implementation Status

## Milestones

- [x] Repo scaffold, docs, packaging, pre-commit hook
- [x] Thesis clarified: intraday single-tenor mean-reversion on a constant level (EUR 50Y IRS), delayed-close execution strategy
- [x] DataFrame contract revised for intraday single-tenor level-space shape
- [x] First DGP trio scaffolded: `want/ou_with_noise`, `dont_want/random_walk_with_noise`, `dont_want/ou_no_noise`
- [x] Tests for each DGP: contract conformance + claimed statistical property
- [x] Layer-1 notebook skeleton: `00_granularity_selection.ipynb` (cells labelled, methodology cells empty)
- [x] Literature-grounded starter parameter values for the `want/ou_with_noise` DGP (see `PARAMETER_SOURCES.md`)
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
