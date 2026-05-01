# Next Session Checklist

Purpose: run the live bQuant handoff without moving raw Bloomberg data out of bQuant.

## Colleague prepares in bQuant

- Create a pandas DataFrame named `df`.
- Use a timezone-aware `DatetimeIndex`, ideally CET/session-local.
- Include one numeric EUR swap-rate level column, preferably `50Y`, `30Y`, `20Y`, or `10Y`.
- Keep values as decimal rate levels, not percent strings and not returns.
- Target intraday one-minute observations for the [08:00, 17:00) session.

## Paste first

Paste `bquant_snippets/00_data_audit.py` first.

If it prints `STAGE_STATUS: pass`, continue to `bquant_snippets/01_granularity_pathb.py`.

If it prints `STAGE_STATUS: review`, verbally report the warning lines before continuing.

## Readouts to report

Read back only compact aggregate diagnostics:

- `DATA_AUDIT`
- `RATE_COL`
- `N_OBS`
- `TZ_AWARE`
- `MEDIAN_FREQUENCY_MIN`
- `SESSION_DAYS`
- `COMPLETE_SESSIONS_540`
- `PARTIAL_SESSIONS`
- `SESSION_BARS_MIN_MEDIAN_MAX`
- any `WARNING:` lines
- from Layer 1: `LAYER1_PATH`, `DELTA_GRID`, `OU_HALF_LIFE_MIN`, `WEDGE_TOL`, `DELTA_STAR`, `NOISE_WEDGE_BY_DELTA`

## Do not share

- raw timestamped rate rows;
- Bloomberg screenshots or terminal output;
- proprietary prices, curves, identifiers, or field mnemonics beyond the agreed public column name;
- client, counterparty, trader, trade, order, ticket, or account identifiers;
- exported files, copied tables, or pasted DataFrame contents.
