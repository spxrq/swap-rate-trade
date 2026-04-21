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

### Changed
- `docs/DATA_CONTRACT.md` rewritten for intraday single-tenor level-space shape (1-minute base resolution, 08:00–17:00 CET session, single column `50Y`).

### Archived
- Original `nb0`–`nb5` template + README moved to `archive/template_reference/` for reference only.
