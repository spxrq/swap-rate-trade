# swap-rate-trade

Research scaffold for statistical-arbitrage trading on long-tenor swap rates (20y / 30y / 50y). Short tenors (< 10y) are out of scope.

## Purpose

Two parallel layers:

1. **Synthetic data layer (`synthetic/`)** — adversarial data-generating processes (DGPs) we build to validate our methods before live data is touched.
   - **`synthetic/want/`** — DGPs that match our thesis (e.g. mean-reverting spreads, cointegrated tenors). A sound method should work on these.
   - **`synthetic/dont_want/`** — DGPs that break our thesis (e.g. independent random walks). A sound method *must fail* on these. If it doesn't, it's a false positive and disqualified.

2. **Research notebooks (`notebooks/`)** — compartmentalized, step-by-step econometric analysis. Each notebook takes a DataFrame matching the [data contract](docs/DATA_CONTRACT.md) and does one well-scoped research step.

## bQuant handoff

The whole scaffold is designed to be paste-ready into Bloomberg's bQuant environment:
- No Bloomberg SDK wrappers, no data-retrieval classes.
- Notebooks assume a DataFrame is already handed in. Locally it comes from `synthetic/`; in bQuant it comes from `bql`.
- Paste whole notebooks or cell-by-cell into bQuant with minimal rewrites.

See [`docs/BQUANT_COMPAT.md`](docs/BQUANT_COMPAT.md) for the living library-allowlist.

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

## Status

See [`docs/IMPLEMENTATION_STATUS.md`](docs/IMPLEMENTATION_STATUS.md).
