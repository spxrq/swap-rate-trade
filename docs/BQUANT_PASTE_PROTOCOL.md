# bQuant Paste Protocol

Purpose: make the public repo useful during live Bloomberg/bQuant sessions without moving bank data, terminal output, screenshots, proprietary prices, client names, or internal order data into the repo.

## Working Rule

The public repo owns methodology code. bQuant owns data access.

Most bQuant-ready snippets should assume exactly one input object:

```python
df = ...
```

Locally, `df` can come from synthetic smoke-test data. In bQuant, `df` comes from a Bloomberg query and must match `docs/DATA_CONTRACT.md` or the looser contract stated in the snippet. The Excel research starter is the exception: it assumes a bQuant-local `EXCEL_PATH` and sheets named like `timestamp5`, `timestamp60`, etc.

Everything after the bQuant `df` assignment should be paste-ready and should avoid:

- filesystem reads;
- local package imports such as `from synthetic...`;
- Bloomberg wrappers inside methodology cells;
- institution-specific names or confidential identifiers;
- raw data exports in printed output.

## Live Iteration Loop

1. Repo operator edits `bquant_snippets/*.py`.
2. Colleague pastes the updated cell block into bQuant.
3. bQuant prints only compact operator readouts.
4. Colleague verbally reports the readout values.
5. Repo operator adjusts public code.

This lets the methodology iterate quickly without transferring bank data out of Bloomberg.

## Safe Operator Readouts

Prefer summaries that are useful but non-sensitive:

```text
DATA_CHECK: pass
RATE_COL: 10Y
N_OBS: 14320
SESSION_DAYS: 28
DELTA_GRID: [5, 15, 30, 60, 120]
OU_THETA_PER_MIN: 0.0112
OU_HALF_LIFE_MIN: 61.9
DELTA_STAR: 15
NOISE_WEDGE_5M: 0.064
NOISE_WEDGE_15M: 0.023
WARNING: theta estimate unstable
```

Do not print raw timestamped rates, trade IDs, counterparties, or execution details.

## Snippet Pattern

Each paste snippet should follow this order:

1. Imports from the bQuant allowlist.
2. Config cell: `RATE_COL`, session times, delta grid, tolerances.
3. Comment that bQuant must already provide `df`.
4. `validate_input_df(df)` or audit cell.
5. Pure methodology cells.
6. Operator readout cell.

## Current Handoff Sequence

The live bQuant handoff sequence is:

```text
bquant_snippets/00_data_audit.py
bquant_snippets/01_granularity_pathb.py
optional: bquant_snippets/02_excel_research_starter.py
future: bquant_snippets/03_mean_reversion_*.py
future: bquant_snippets/04_execution_window_*.py
```

The important Layer-1 change is methodological: do not select sampling frequency by looking for a textbook RV plateau. For an OU process over a short session, the no-noise RV curve is not flat. Use the OU-implied RV null and diagnose the microstructure-noise wedge instead.
