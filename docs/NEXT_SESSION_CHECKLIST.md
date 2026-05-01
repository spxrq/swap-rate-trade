# Next Research Checklist

Purpose: run the local Excel research workflow cleanly.

## Prepare Data

- Save the workbook locally.
- Name sheets `timestamp5`, `timestamp15`, `timestamp30`, `timestamp60`, etc.
- Include a timestamp column and at least one numeric rate-level column, preferably `50Y`, `30Y`, `20Y`, or `10Y`.
- Keep values as decimal rate levels, not percent strings and not returns.
- Use session-local timestamps where possible.

## Run Order

1. Set `EXCEL_PATH`.
2. Run `research_snippets/02_excel_research_starter.py`.
3. Confirm the loaded frames exist, especially `df_5`.
4. Use 5m as the working granularity if RV/BV does not show meaningful fine-grid inflation.
5. Run `research_snippets/03_mean_reversion_starter.py`.

## Readouts To Record

- `RATE_COL`
- `LOADED_DELTAS`
- `CREATED_FRAMES`
- `CANDIDATE_DELTA_HEURISTIC`
- `CHANGE_ACF_LAG1`
- `SQ_CHANGE_ACF_LAG1`
- `AR1_PHI`
- `AR1_HALF_LIFE_MIN`
- `AUTOREG_SELECTED_LAGS`
- `AUTOREG_HALF_LIFE_MIN_DOMINANT_ROOT`
- `ADF_PVALUE_LEVEL`
- `KPSS_PVALUE_LEVEL`
- `BREUSCH_GODFREY_PVALUE_AR1_RESID`
- `BREUSCH_PAGAN_PVALUE_AR1_RESID`
- `ARCH_LM_PVALUE_AR1_RESID`
