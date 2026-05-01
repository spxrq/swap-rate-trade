# Public Repo Safety

This repository is methodology infrastructure for local Excel-based research.

## Allowed content

- methodology code that uses the local Python econometrics stack;
- synthetic or dummy smoke-test data with known parameters;
- notebook-ready research snippets;
- aggregate diagnostics, warning text, and decision rules;
- documentation for the public workflow and data contract.

## Forbidden content

- raw timestamped empirical rows unless intentionally committed as an approved sample;
- screenshots or copied terminal output;
- trade/order IDs, tickets, client names, counterparty names, or desk-specific identifiers;
- empirical conclusions that depend on data whose provenance and cleaning are not documented.

## Safe Research Readouts

Examples that are safe to read aloud or paste into notes:

```text
DATA_AUDIT: pass
RATE_COL: 10Y
N_OBS: 5400
TZ_AWARE: True
MEDIAN_FREQUENCY_MIN: 1.000
SESSION_DAYS: 10
COMPLETE_SESSIONS_540: 10
STAGE_STATUS: pass
```

```text
LAYER1_PATH: OU noise-wedge
DELTA_GRID: [5, 15, 30, 60, 120]
OU_HALF_LIFE_MIN: 62.4
WEDGE_TOL: 0.050
DELTA_STAR: 15
NOISE_WEDGE_BY_DELTA: 5m=0.071, 15m=0.032, 30m=0.018, 60m=0.010, 120m=0.006
```

If a readout includes raw rows, screenshots, identifiers, or undocumented exact prices, do not move it into this repo.
