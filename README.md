# swap-rate-trade

Research scaffold for intraday EUR swap-rate execution-timing methodology using locally saved Excel data, synthetic smoke tests, and notebook-ready Python snippets.

## Purpose

Two layers:

1. **Synthetic data layer (`synthetic/`)** — dummy data-generating processes (DGPs) for smoke tests and known-parameter validation before empirical data is used. Synthetic results do not decide empirical conclusions.
   - **`synthetic/want/`** — DGPs that match our thesis, such as mean-reverting spreads or cointegrated tenors. A sound method should work on these.
   - **`synthetic/dont_want/`** — DGPs that break our thesis, such as independent random walks. A sound method must fail on these.

2. **Excel research layer (`research_snippets/`)** — notebook-style Python cells for loading manually saved Excel sheets and running econometric diagnostics.

The empirical workflow starts from an Excel workbook with sheets named like `timestamp5`, `timestamp15`, `timestamp60`, etc. The code creates separate DataFrames such as `df_5` and `df_60`.

## Research Workflow

1. Save the market data workbook locally.
2. Set `EXCEL_PATH` to that workbook.
3. Run `research_snippets/02_excel_research_starter.py` to load the timestamp sheets, inspect distributions, ACF/PACF, and RV/BV.
4. Use 5m as the current working granularity if the RV/BV signature does not show meaningful fine-grid inflation.
5. Run `research_snippets/03_mean_reversion_starter.py` to inspect level persistence, 5m reversal, squared-change clustering, AR models, ADF, KPSS, Ljung-Box, and residual diagnostics.

Layer 1 now uses the OU-implied RV null and microstructure-noise wedge. Do not rely only on the textbook "find where RV stabilizes" rule for the OU regime.

## Quickstart

```bash
git clone git@github.com:spxrq/swap-rate-trade.git
cd swap-rate-trade

python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e .

pre-commit install

jupyter lab
```

## Structure

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for how the pieces fit together.

Current research helpers:

- [`research_snippets/00_data_audit.py`](research_snippets/00_data_audit.py) — audits an already-created `df` for usable tenor columns, frequency, missingness, duplicates, and session completeness.
- [`research_snippets/01_granularity_pathb.py`](research_snippets/01_granularity_pathb.py) — Layer-1 OU noise-wedge granularity diagnostic for a single clean input frame.
- [`research_snippets/02_excel_research_starter.py`](research_snippets/02_excel_research_starter.py) — Excel workbook loader for sheets named `timestamp5`, `timestamp60`, etc.; creates `df_5`, `df_60`, distribution diagnostics, ACF/PACF plots, and RV/BV summaries.
- [`research_snippets/03_mean_reversion_starter.py`](research_snippets/03_mean_reversion_starter.py) — second-stage 5m mean-reversion diagnostics for levels, first differences, squared differences, AR/AR(1), ADF, KPSS, Ljung-Box, Breusch-Godfrey, Breusch-Pagan, and ARCH LM tests.

## Status

See [`docs/IMPLEMENTATION_STATUS.md`](docs/IMPLEMENTATION_STATUS.md).
