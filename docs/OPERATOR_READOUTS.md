# Operator Readouts

Research readouts are short text summaries for recording notebook diagnostics without dumping full raw data tables.

## Rules

- Print aggregate diagnostics only.
- Round values enough for decisions.
- Include warnings when assumptions are weak.
- Avoid printing raw rate rows, trade identifiers, counterparties, client names, or screenshots.

## Standard Header

Every research snippet should print something close to:

```text
DATA_CHECK: pass
RATE_COL: 50Y
N_OBS: 540
START: redacted/session-local
END: redacted/session-local
TZ_AWARE: true
MONOTONIC: true
MISSING_VALUES: 0
```

For public discussion, dates can be omitted or coarsened to counts.

## Layer 1 Granularity Readout

```text
LAYER1_PATH: OU noise-wedge
DELTA_GRID: [5, 15, 30, 60, 120]
OU_THETA_PER_MIN: 0.01155
OU_HALF_LIFE_MIN: 60.0
OU_SIGMA_EFF: 3.80e-05
WEDGE_TOL: 0.05
DELTA_STAR: 15
NOISE_WEDGE_BY_DELTA: 5m=0.065, 15m=0.023, 30m=0.013, 60m=0.008, 120m=0.004
SIGMA_N_SQ_EST_SMALL_DELTA: 2.32e-10
WARNINGS: none
```

If the rule does not select a frequency:

```text
DELTA_STAR: ambiguous
WARNINGS: no delta below wedge tolerance; widen grid or review OU/noise fit
```

## Stage Decision Language

Use decision language that separates code execution from research conclusion:

- `pass`: the cell ran and inputs match contract.
- `review`: methodology ran but assumptions or diagnostics need human judgment.
- `fail`: input shape or model fit is not usable.

Examples:

```text
STAGE_STATUS: pass
STAGE_STATUS: review - theta estimate unstable
STAGE_STATUS: fail - df index is not timezone-aware
```
