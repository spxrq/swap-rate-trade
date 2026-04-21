# Architecture

## Flow

```
┌────────────────────┐         ┌────────────────────┐
│  synthetic/want/   │         │ synthetic/dont_    │
│  (thesis DGPs)     │         │ want/ (null DGPs)  │
└─────────┬──────────┘         └─────────┬──────────┘
          │                              │
          └──────────────┬───────────────┘
                         ▼
           ┌────────────────────────────┐
           │ DataFrame (data contract)  │
           │ index  = timestamp         │
           │ cols   = tenors            │
           │ values = close / mid rate  │
           └─────────────┬──────────────┘
                         ▼
           ┌────────────────────────────┐
           │        notebooks/          │
           │  step-by-step research     │
           └─────────────┬──────────────┘
                         ▼
           ┌────────────────────────────┐
           │    bQuant (Bloomberg)      │
           │    paste cells, run with   │
           │    real swap-rate data     │
           └────────────────────────────┘
```

## The DataFrame contract

See [`docs/DATA_CONTRACT.md`](docs/DATA_CONTRACT.md) for the authoritative spec.

At a high level, every notebook consumes (and sometimes produces) DataFrames with a datetime index, columns named by tenor (e.g. `20Y`, `30Y`, `50Y`), and numeric values representing close or mid prices/rates.

Locally, the DataFrame is produced by a synthetic DGP. In bQuant, the same-shaped DataFrame is sourced from `bql`. Because the contract is identical, notebook cells transplant directly.

## Validation principle

A method is validated by a **Monte Carlo criterion over many simulated paths**, not by a single realization. Null DGPs are stochastic — at nominal significance α, a properly-sized test on `dont_want/` data will falsely reject at rate α *by construction*, so a single-path comparison is unsound.

Baseline thresholds:

- **Power** on `synthetic/want/`: over **N = 500** paths, the method must detect the target property with frequency ≥ **β = 0.9**.
- **Type-I control** on `synthetic/dont_want/`: over **N = 500** paths, the method must detect the property with frequency ≤ **α = 0.05**, with a **1.5×** finite-sample tolerance in automated tests (FPR ≤ 0.075).

A method is accepted only when both criteria hold.

## Why separate `synthetic/` from `notebooks/`

- DGPs are pure functions — worth unit-testing in `tests/`.
- Notebooks are for exploration, presentation, and paste-to-bQuant.
- Keeping DGPs out of notebooks means we can swap the data source without touching research code.

## Why separate `want/` from `dont_want/`

- Makes the adversarial pairing structural, not a convention we might forget.
- A new method is only accepted into the toolkit if we have run it against at least one DGP from each folder and seen the expected pass/fail pattern.
