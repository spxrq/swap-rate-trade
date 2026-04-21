# DGP Catalog

Living catalog of data-generating processes used in this project. Add a row whenever a new DGP is introduced.

## `synthetic/want/` — thesis-matching DGPs

A sound method **must** work on these.

| Name | File | Description | Parameters | Status |
|------|------|-------------|------------|--------|
| _none yet_ | | | | |

## `synthetic/dont_want/` — adversarial / null DGPs

A sound method **must fail** on these. A method that "succeeds" here is a false positive.

| Name | File | Description | Parameters | Status |
|------|------|-------------|------------|--------|
| _none yet_ | | | | |

## Conventions

- Every DGP function takes explicit parameters (seed, length, etc.) and returns a DataFrame that conforms to `DATA_CONTRACT.md`.
- Every DGP has at least one test in `tests/` that verifies the statistical property the DGP claims (e.g. "this `want` DGP produces a cointegrated pair at p < 0.01 over N simulations").
