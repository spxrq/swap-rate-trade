# Data Contract

The canonical shape of the DataFrame that moves between `synthetic/` DGPs, `notebooks/`, and bQuant.

## Shape

| Axis    | Meaning                                          |
|---------|--------------------------------------------------|
| Index   | Timestamps (pandas `DatetimeIndex`), monotonic   |
| Columns | Tenors as strings, e.g. `20Y`, `30Y`, `50Y`      |
| Values  | Close or mid prices/rates (numeric, `float64`)   |

## Minimal example

```
              20Y     30Y     50Y
2024-01-02  4.321   4.298   4.210
2024-01-03  4.318   4.295   4.208
...
```

## Rules

- **Tenors of interest: 20Y, 30Y, 50Y.** Shorter tenors (< 10Y) are out of scope.
- Column order is not semantically meaningful; notebooks and DGPs must reference columns by name.
- Values are `float64`.

## To be decided (discuss before locking in)

- Sampling frequency (daily close? tick-level? business-day calendar?).
- Missing-value convention (drop? forward-fill? explicit `NaN` preserved?).
- Timezone handling (naive? UTC? market-local?).
- Close vs mid — single choice repo-wide, or configurable per DGP?

## Why a strict contract

A single, strict shape is what lets us:
1. swap `synthetic/` DGPs in and out without touching notebooks,
2. paste notebook cells directly into bQuant (which sources the same-shaped DataFrame via `bql`),
3. unit-test DGPs by asserting their output conforms.

## Change process

Changing this contract is a **RED-level** decision. Stop and discuss before editing this file.
