# Public Repo Safety

This repository is public methodology infrastructure. Bloomberg/bQuant remains the data boundary.

## Allowed content

- methodology code that uses `numpy`, `pandas`, and `matplotlib`;
- synthetic or dummy smoke-test data with known parameters;
- paste-ready bQuant snippets that assume `df` already exists;
- aggregate diagnostics, warning text, and decision rules;
- documentation for the public workflow and data contract.

## Forbidden content

- real Bloomberg data or exported bQuant files;
- screenshots, copied terminal output, or raw timestamped rates;
- proprietary prices, curves, trade/order IDs, tickets, client names, counterparty names, or desk-specific identifiers;
- filesystem reads inside bQuant snippets;
- Bloomberg query code that embeds confidential tickers, universes, portfolios, or internal conventions;
- empirical conclusions that depend on real data unless they are stated only as safe aggregate readouts from bQuant.

## Safe operator readouts

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

If a readout includes raw rows, timestamps, screenshots, identifiers, or exact proprietary prices, do not move it into this repo.
