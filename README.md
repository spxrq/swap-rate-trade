# swap-rate-trade

Public research scaffold for intraday EUR swap-rate execution-timing methodology. Real Bloomberg/bQuant data stays inside bQuant. This repo contains only public code, documentation, synthetic smoke tests, and paste-ready snippets that print compact aggregate diagnostics.

## Purpose

Two layers:

1. **Synthetic data layer (`synthetic/`)** — dummy data-generating processes (DGPs) for smoke tests and known-parameter validation before live data is touched. Synthetic results do not decide empirical conclusions.
   - **`synthetic/want/`** — DGPs that match our thesis (e.g. mean-reverting spreads, cointegrated tenors). A sound method should work on these.
   - **`synthetic/dont_want/`** — DGPs that break our thesis (e.g. independent random walks). A sound method *must fail* on these. If it doesn't, it's a false positive and disqualified.

2. **bQuant handoff layer (`bquant_snippets/`)** — paste-ready methodology cells. A colleague creates a DataFrame named `df` inside bQuant, pastes the public snippet, and reports only compact aggregate readouts. Notebooks are kept as non-canonical development references.

The public repo never needs raw Bloomberg rows. bQuant supplies `df`; this repo supplies the method.

## bQuant handoff

The live workflow is:

1. Build or revise public methodology code here.
2. In bQuant, create `df` from Bloomberg data.
3. Paste `bquant_snippets/00_data_audit.py` first.
4. If the audit passes or the warnings are understood, paste `bquant_snippets/01_granularity_pathb.py`.
5. Verbally report only aggregate lines such as `DATA_AUDIT`, `SESSION_DAYS`, `DELTA_STAR`, and `NOISE_WEDGE_BY_DELTA`.
6. Do not export raw data, screenshots, timestamps, trade/order IDs, client names, or proprietary desk information.

See [`docs/BQUANT_COMPAT.md`](docs/BQUANT_COMPAT.md) for the living library-allowlist.

For live collaboration, use [`docs/NEXT_SESSION_CHECKLIST.md`](docs/NEXT_SESSION_CHECKLIST.md), [`docs/PUBLIC_REPO_SAFETY.md`](docs/PUBLIC_REPO_SAFETY.md), [`docs/BQUANT_PASTE_PROTOCOL.md`](docs/BQUANT_PASTE_PROTOCOL.md), and [`docs/OPERATOR_READOUTS.md`](docs/OPERATOR_READOUTS.md).

Layer 1 now uses the OU-implied RV null and microstructure-noise wedge. Do not use the textbook "find where RV stabilizes" rule for the OU regime.

## Quickstart (local)

```bash
git clone git@github.com:spxrq/swap-rate-trade.git
cd swap-rate-trade

python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e .            # makes `from synthetic.want import ...` work anywhere

pre-commit install          # enables nbstripout — strips notebook outputs on every commit

jupyter lab
```

## Structure

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for how the pieces fit together.

Current paste-ready helpers:

- [`bquant_snippets/00_data_audit.py`](bquant_snippets/00_data_audit.py) — first paste in bQuant; audits a Bloomberg-supplied `df` for usable tenor columns, frequency, missingness, duplicates, and session completeness.
- [`bquant_snippets/01_granularity_pathb.py`](bquant_snippets/01_granularity_pathb.py) — Layer-1 OU noise-wedge granularity diagnostic.

## Status

See [`docs/IMPLEMENTATION_STATUS.md`](docs/IMPLEMENTATION_STATUS.md).
