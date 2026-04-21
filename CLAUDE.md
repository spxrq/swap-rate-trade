# CLAUDE.md — swap-rate-trade

Project-specific instructions for Claude when working on this repo.

## What this project is

A research scaffold for **intraday statistical-arbitrage execution on EUR 50Y IRS** (Phase 1). Other long tenors (20y, 30y) are secondary and can be added later by copying cells; short tenors (< 10y) are out of scope.

Two layers:

1. **`synthetic/`** — adversarial data-generating processes (DGPs). `want/` DGPs match the thesis (intraday mean-reverting rate around a constant level, plus microstructure noise). `dont_want/` DGPs break it (random walks, no noise). A method is validated by a **Monte Carlo criterion over many simulated paths**, not by a single realization. Baseline thresholds: on `synthetic/want/`, power ≥ **β = 0.9** over **N = 500** paths; on `synthetic/dont_want/`, false-positive rate ≤ **α = 0.05** with a **1.5× finite-sample tolerance** (FPR ≤ 0.075). A single null-DGP path looks thesis-consistent by chance roughly α of the time by construction, so path-by-path validation is unsound.
2. **`notebooks/`** — compartmentalized, paste-ready econometric analysis. The interface is the DataFrame contract in `docs/DATA_CONTRACT.md`.

The repo is designed to be paste-ready into Bloomberg's bQuant. No Bloomberg SDK wrappers. No data-retrieval classes.

## How to work on this project

### Default working mode: Claude scaffolds, operator drives

- **Do not freelance research content.** Do not write DGP math, notebook cells, or statistical methodology without the operator's explicit steer. The operator is the econometrician; Claude's job is to scaffold clean implementations from decisions the operator has already made.
- **Proceed notebook by notebook, one at a time.** No batch creation of multiple research notebooks. Confirm scope for each one before starting.
- **No speculative abstraction.** Keep structures flat until real use cases force a refactor.

### Always preserve

- **The DataFrame contract.** Every notebook and every DGP function consumes or produces data matching `docs/DATA_CONTRACT.md`. If you need to change the contract, stop and discuss — it is a RED-level decision.
- **The paste-ready property.** Notebooks must be trivial to paste into bQuant. That means:
  - no filesystem reads inside research cells,
  - no local-only imports without a clearly marked "paste this cell first" block,
  - no libraries outside `docs/BQUANT_COMPAT.md` without flagging it explicitly.
- **Cleared notebook outputs.** `nbstripout` is enforced via pre-commit. Do not commit populated outputs.

### When in doubt

- Ask. This is a multi-week, human-guided project. A pause to confirm is cheaper than a wrong implementation.
- Language level: L2–L3 Python, L4 econometrics / statistics. Use finance analogies for unfamiliar Python/tooling concepts. Technical econometric content can be at full depth.

### Documentation to keep current

- `docs/DGP_CATALOG.md` — when we add a DGP, add its row.
- `docs/BQUANT_COMPAT.md` — when we discover a library is allowed or blocked, add its row.
- `docs/IMPLEMENTATION_STATUS.md` — when we complete a milestone, update it.
- `CHANGELOG.md` — append a short entry on meaningful structural changes.

## HOP classification defaults

- Adding a DGP: typically YELLOW (new statistical primitive).
- Writing a new notebook's methodology: typically YELLOW or RED depending on scope.
- Scaffolding (new empty file, doc update, config tweak): GREEN.
- Changing the DataFrame contract: **always RED.**

## Archive

`archive/template_reference/` holds the original notebook template (`nb0`–`nb5`) from before this scaffold was built. Treat as reference material only. Do **not** import from it, do not assume its code runs, and do not depend on its structure.
