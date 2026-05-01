# Excel Research Protocol

Purpose: keep the empirical workflow reproducible now that data is manually saved in Excel.

## Working Rule

The repository owns methodology code. The local Excel workbook owns empirical data.

The main workbook workflow expects:

```python
EXCEL_PATH = r".../swap_data.xlsx"
```

Expected sheet names:

```text
timestamp5
timestamp15
timestamp30
timestamp60
timestamp120
```

The Excel starter creates:

```python
dfs_by_delta
df_5
df_15
df_30
df_60
returns_by_delta
distribution_summary
rv_bv_summary
```

## Notebook Cell Pattern

Each research snippet should follow this order:

1. Imports from the Python econometrics stack.
2. Config cell: file path, rate column, session times, delta grid, tolerances.
3. Input loading or input validation.
4. Pure methodology cells.
5. Plots and compact summary tables.
6. Short interpretation notes.

## Current Research Sequence

```text
research_snippets/02_excel_research_starter.py
research_snippets/03_mean_reversion_starter.py
future: research_snippets/04_execution_window_*.py
```

The important Layer-1 decision is methodological: if the RV/BV signature does not show meaningful fine-grid inflation at 5m, use 5m as the working granularity for mean-reversion research. Keep that phrased as a working choice, not as proof that noise is absent.
