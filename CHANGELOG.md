# Changelog

All notable structural changes and decisions get a short entry here.

## [Unreleased]

### Added
- Initial scaffold: `synthetic/want/`, `synthetic/dont_want/`, `notebooks/`, `tests/`.
- Docs: `DATA_CONTRACT.md`, `DGP_CATALOG.md`, `BQUANT_COMPAT.md`, `IMPLEMENTATION_STATUS.md`.
- Packaging via `pyproject.toml` + `requirements.txt` (editable install makes `synthetic` importable from anywhere).
- `nbstripout` pre-commit hook to keep notebook outputs out of git.
- `CLAUDE.md` project-specific instructions.
- Intraday mean-reversion thesis locked in: EUR 50Y IRS, delayed-close execution strategy around an 11:00 CET scheduled close.
- First DGP trio: `want/ou_with_noise`, `dont_want/random_walk_with_noise`, `dont_want/ou_no_noise`. Parameters are required keyword-only arguments — no hard-coded "realistic" defaults.
- Pytest tests for each DGP: contract conformance + claimed statistical property.
- Layer-1 notebook skeleton: `notebooks/00_granularity_selection.ipynb` (RV/BV signature-plot research step, methodology cells left empty for operator-led fill-in).
- `docs/PARAMETER_SOURCES.md` — literature-grounded starter parameters for the `want/ou_with_noise` DGP, with derivation, confidence per parameter, and known limitations. Sources: Hansen-Lunde 2006, Fed IFDP 905, Aït-Sahalia-Yu, Fleming-Remolona, Mizrach-Neely, Poutré-Ragel-Cont 2024, Holý-Tomanová, Andersen-Bollerslev, ECB 2005.
- `notebooks/00_granularity_selection.ipynb` data-load cell now instantiates the `want/ou_with_noise` DGP with literature-grounded parameters — notebook can run end-to-end from data generation onward.

### Changed (post-audit, second-opinion review via Codex)
- **Validation principle rewritten as Monte Carlo.** Single-path "must succeed on `want/` and fail on `dont_want/`" was unsound: null DGPs are stochastic, and a properly-sized α-level test false-rejects at rate α by construction. New framing requires power ≥ β on `want/` and FPR ≤ α (with 1.5× finite-sample tolerance) on `dont_want/`. Baseline: N=500, α=0.05, β=0.9. Applied to `CLAUDE.md`, `ARCHITECTURE.md`, `docs/DGP_CATALOG.md`.
- **Tests rewritten from single-path assertions to Monte Carlo harnesses.** `test_adf_power_on_want_dgp` replaces `test_series_is_stationary`; `test_adf_false_positive_rate_under_unit_root` replaces `test_series_has_unit_root`. `ou_no_noise` keeps a single-path smoke test with an explicit TODO to replace once Layer-1 methodology exists.
- **Session length normalised.** `DATA_CONTRACT.md` now explicit about half-open `[08:00, 17:00)` = 540 bars indexed `08:00, …, 16:59`. Example timestamps corrected.
- **DGPs fail fast on naive timestamps.** All three `simulate()` functions raise `ValueError` on `start.tz is None`.
- **`PARAMETER_SOURCES.md` restructured.** Each claim tagged `[V]` verified or `[A]` author-extrapolation so a reader can tell what's literature-grounded vs judgment. σ_noise derivation flagged as small-θ approximation (~0.6% error at our θ). New "Assumptions embedded in the current DGP" section documents OU-starts-at-μ and other baked-in modelling choices.
- **`CLAUDE.md` project scope** narrowed from "20y/30y/50y" to "EUR 50Y IRS (Phase 1)" to match reality.

### Changed
- `docs/DATA_CONTRACT.md` rewritten for intraday single-tenor level-space shape (1-minute base resolution, 08:00–17:00 CET session, single column `50Y`).

### Archived
- Original `nb0`–`nb5` template + README moved to `archive/template_reference/` for reference only.
