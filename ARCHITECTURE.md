# Architecture

## Flow

```text
synthetic/want/ and synthetic/dont_want/
        |
        v
DataFrame contract
        |
        v
notebooks/ and research_snippets/
        |
        v
local Excel empirical workflow
```

## The DataFrame Contract

See [`docs/DATA_CONTRACT.md`](docs/DATA_CONTRACT.md) for the authoritative spec.

At a high level, every notebook consumes DataFrames with a datetime index, columns named by tenor such as `20Y`, `30Y`, or `50Y`, and numeric values representing rate levels.

For synthetic validation, the DataFrame is produced by a DGP. For empirical work, the DataFrame is loaded from a local Excel workbook with sheets such as `timestamp5` and `timestamp60`.

## Validation Principle

A method is validated by a Monte Carlo criterion over many simulated paths, not by a single realization. Null DGPs are stochastic: at nominal significance alpha, a properly-sized test on `dont_want/` data will falsely reject at rate alpha by construction, so a single-path comparison is unsound.

Baseline thresholds:

- **Power** on `synthetic/want/`: over `N = 500` paths, the method must detect the target property with frequency at least `beta = 0.9`.
- **Type-I control** on `synthetic/dont_want/`: over `N = 500` paths, the method must detect the property with frequency at most `alpha = 0.05`, with a `1.5x` finite-sample tolerance in automated tests.

A method is accepted only when both criteria hold.

## Why Separate `synthetic/` From `notebooks/`

- DGPs are pure functions and worth unit-testing in `tests/`.
- Notebooks are for exploration and presentation.
- Keeping DGPs out of notebooks means we can swap the data source without touching research code.

## Why Separate `want/` From `dont_want/`

- Makes the adversarial pairing structural.
- A new method is only accepted into the toolkit if we have run it against at least one DGP from each folder and seen the expected pass/fail pattern.
