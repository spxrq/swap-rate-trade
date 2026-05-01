# Changelog

All notable structural changes and decisions get a short entry here.

## [Unreleased]

### Added
- Local Excel research workflow docs: `docs/EXCEL_RESEARCH_PROTOCOL.md` and `docs/OPERATOR_READOUTS.md`.
- `research_snippets/00_data_audit.py` for DataFrame availability/frequency/session auditing.
- `research_snippets/01_granularity_pathb.py` for a notebook-ready Layer-1 OU noise-wedge granularity diagnostic.
- Initial scaffold: `synthetic/want/`, `synthetic/dont_want/`, `notebooks/`, `tests/`.
- Docs: `DATA_CONTRACT.md`, `DGP_CATALOG.md`, `PYTHON_ECONOMETRICS.md`, `IMPLEMENTATION_STATUS.md`.
- Packaging via `pyproject.toml` + `requirements.txt` (editable install makes `synthetic` importable from anywhere).
- `nbstripout` pre-commit hook to keep notebook outputs out of git.
- Intraday mean-reversion thesis locked in: EUR 50Y IRS, delayed-close execution strategy around an 11:00 CET scheduled close.
- First DGP trio: `want/ou_with_noise`, `dont_want/random_walk_with_noise`, `dont_want/ou_no_noise`. Parameters are required keyword-only arguments — no hard-coded "realistic" defaults.
- Pytest tests for each DGP: contract conformance + claimed statistical property.
- Layer-1 notebook skeleton: `notebooks/01_granularity_selection.ipynb` (RV/BV signature-plot research step, methodology cells left empty for operator-led fill-in).
- `docs/PARAMETER_SOURCES.md` — literature-grounded starter parameters for the `want/ou_with_noise` DGP, with derivation, confidence per parameter, and known limitations. Sources: Hansen-Lunde 2006, Fed IFDP 905, Aït-Sahalia-Yu, Fleming-Remolona, Mizrach-Neely, Poutré-Ragel-Cont 2024, Holý-Tomanová, Andersen-Bollerslev, ECB 2005.
- `notebooks/01_granularity_selection.ipynb` data-load cell now instantiates the `want/ou_with_noise` DGP with literature-grounded parameters — notebook can run end-to-end from data generation onward.
- `notebooks/00_dgp_design.ipynb` — readable LaTeX-first DGP design record covering OU dynamics, exact discretisation, additive quote noise, negative return autocorrelation, the three DGPs, parameter choices, and Monte Carlo validation.

### Changed (post-audit, second-opinion review)
- **Validation principle rewritten as Monte Carlo.** Single-path "must succeed on `want/` and fail on `dont_want/`" was unsound: null DGPs are stochastic, and a properly-sized α-level test false-rejects at rate α by construction. New framing requires power ≥ β on `want/` and FPR ≤ α (with 1.5× finite-sample tolerance) on `dont_want/`. Baseline: N=500, α=0.05, β=0.9. Applied to `ARCHITECTURE.md` and `docs/DGP_CATALOG.md`.
- **Tests rewritten from single-path assertions to Monte Carlo harnesses.** `test_adf_power_on_want_dgp` replaces `test_series_is_stationary`; `test_adf_false_positive_rate_under_unit_root` replaces `test_series_has_unit_root`. `ou_no_noise` keeps a single-path smoke test with an explicit TODO to replace once Layer-1 methodology exists.
- **Session length normalised.** `DATA_CONTRACT.md` now explicit about half-open `[08:00, 17:00)` = 540 bars indexed `08:00, …, 16:59`. Example timestamps corrected.
- **DGPs fail fast on naive timestamps.** All three `simulate()` functions raise `ValueError` on `start.tz is None`.
- **`PARAMETER_SOURCES.md` restructured.** Each claim tagged `[V]` verified or `[A]` author-extrapolation so a reader can tell what's literature-grounded vs judgment. σ_noise derivation flagged as small-θ approximation (~0.6% error at our θ). New "Assumptions embedded in the current DGP" section documents OU-starts-at-μ and other baked-in modelling choices.

### Added (Layer-1 notebook scaffolding — pre-methodology)
- `notebooks/01_granularity_selection.ipynb` expanded to 22 cells with every design decision and modelling assumption documented explicitly. New content:
  - "Design decisions and assumptions" section (return definition, aggregation, non-overlapping returns, multi-session averaging, stabilisation criterion, parameter confidence, adversarial validation, not-modelled list).
  - Section 2 "Multi-session generation" with `N_SESSIONS=100`, seed-offsetting, and a reusable `generate_sessions()` helper.
  - Section 3 aggregation helper: `resample_last()` + a per-Δ `candles` dict.
  - Section 7 adversarial sanity check — mirror the RV/BV/signature-plot analysis on `dont_want/ou_no_noise`. Seeds the future Monte Carlo type-I test for that DGP.
  - Section 9 "Select Δ\*" now carries forward three open concerns: parameter sensitivity, null-curve flatness, heteroskedasticity.
- Methodology cells (RV, BV, signature-plot construction) remain `TODO(operator-led)`. Notebook runs end-to-end without error.
- Renamed the granularity notebook from `00_granularity_selection.ipynb` to `01_granularity_selection.ipynb` so the DGP design record can sit first in the sequence.

### Added (Layer-1 notebook methodology)
- `notebooks/01_granularity_selection.ipynb` now implements rate-change helpers, RV, BV, cross-session aggregation, thesis/null signature plots, a diagnostic table, and a provisional Δ* adjacent-drop rule.
- The notebook records the comparison-audit caveat that `dont_want/ou_no_noise` is not a guaranteed flat RV-signature null under level-space non-overlapping RV; OU mean reversion can itself make summed RV decline with Δ.

### Changed
- `docs/DGP_CATALOG.md` and `docs/IMPLEMENTATION_STATUS.md` now flag the OU-no-noise null interpretation as under review instead of treating flatness as guaranteed.

### Changed
- `docs/DATA_CONTRACT.md` rewritten for intraday single-tenor level-space shape (1-minute base resolution, 08:00–17:00 CET session, single column `50Y`).

### Archived
- Original `nb0`–`nb5` template + README moved to `archive/template_reference/` for reference only.
