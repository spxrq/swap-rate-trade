# Data Contract

The canonical shape of the DataFrame that moves between `synthetic/` DGPs, `bquant_snippets/`, reference notebooks, and bQuant.

## Current scope (Phase 1)

- **One tenor**: EUR 50Y IRS. The longest liquid tenor is the most liquidity-constrained and has the most economic value for the delayed-close execution strategy. Other tenors can be added later by copying cells.
- **Intraday**, single-session scope.
- **Base resolution**: 1 minute. Finer than the finest candle (5 min) we will analyse, so we have headroom to construct realized variance and bipower variation at multiple granularities.
- **Candle grid for analysis**: Δ ∈ {5, 15, 30, 60, 120} min.
- **Session**: half-open **[08:00, 17:00) CET** — **540 one-minute bars** indexed `08:00, 08:01, …, 16:59`. `17:00` is the session close and is excluded from the index.
- **Value space**: rate **level** in decimal form (e.g. `0.0432` = 4.32%).
  - PnL is quoted in basis points, which is a level difference.
  - Log-level is nearly identical over intraday moves and cannot represent negative rates.
  - Returns (first differences) test mean-reversion of the *increment* series, which is a different object and not what we want.

## Shape

| Axis    | Meaning                                                              |
|---------|----------------------------------------------------------------------|
| Index   | `DatetimeIndex`, timezone-aware (CET), monotonic, 1-minute frequency |
| Columns | Tenor labels as strings. Phase 1: single column `50Y`.               |
| Values  | Rate levels (decimal, `float64`)                                     |

## Minimal example

```
                             50Y
2024-01-02 08:00:00+01:00  0.04321
2024-01-02 08:01:00+01:00  0.04322
2024-01-02 08:02:00+01:00  0.04319
...
2024-01-02 16:59:00+01:00  0.04315
```

## Rules

- Column order is not semantically meaningful; snippets reference columns by name.
- Missing values: not permitted within a simulated session (DGP output is always complete). Real bQuant data may have gaps — handling deferred to Phase 2.
- Timezone: CET tz-aware. bQuant may return UTC or session-local; convert on import.

## What the contract buys us

1. **DGPs swap in and out** without touching methodology code.
2. **Paste-ready:** a snippet that expects this shape works identically whether the input came from `synthetic/` or from bQuant's `bql`.
3. **Testable:** every DGP has a shape-conformance test.

## Change process

Changing this contract is **RED-level**. Discuss before editing.
