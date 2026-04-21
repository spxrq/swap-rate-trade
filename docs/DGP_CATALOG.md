# DGP Catalog

## `synthetic/want/` — thesis-matching DGPs

| Name | File | Description | Parameters | Status |
|------|------|-------------|------------|--------|
| OU + microstructure noise | `want/ou_with_noise.py` | Ornstein–Uhlenbeck efficient price mean-reverting to `μ` with half-life `ln(2)/θ`, plus iid Gaussian microstructure noise. Supports both Layer-1 (microstructure detection via RV/BV) and Layer-2 (mean-reversion detection) analysis. | `μ`, `θ`, `σ_eff`, `σ_noise`, `n_minutes`, `start`, `seed` | Scaffolded; literature-grounded starter parameters in `PARAMETER_SOURCES.md` |

## `synthetic/dont_want/` — adversarial / null DGPs

| Name | File | Description | Negates | Parameters | Status |
|------|------|-------------|---------|------------|--------|
| Random walk + noise | `dont_want/random_walk_with_noise.py` | Random-walk efficient price plus iid Gaussian microstructure noise. | Mean-reversion | `start_level`, `σ_eff`, `σ_noise`, `n_minutes`, `start`, `seed` | Scaffolded |
| OU, no noise | `dont_want/ou_no_noise.py` | Pure OU efficient price; no microstructure noise overlay. Signature plot should be approximately flat. | Microstructure noise | `μ`, `θ`, `σ_eff`, `n_minutes`, `start`, `seed` | Scaffolded |

## Validation principle

A method is accepted only when:
1. It **succeeds** on `want/ou_with_noise` (detects microstructure noise at fine Δ; detects mean-reversion at the chosen Δ*).
2. It **fails to detect mean-reversion** on `dont_want/random_walk_with_noise`.
3. It **fails to detect microstructure noise** on `dont_want/ou_no_noise` (signature plot approximately flat).

## Conventions

- Every DGP function uses keyword-only arguments. No positional params.
- Every DGP accepts a `seed` for reproducibility.
- Every DGP returns a DataFrame conforming to `DATA_CONTRACT.md`.
- Every DGP has at least one test in `tests/` that verifies its claimed statistical property.
- DGP function signatures have no hard-coded "realistic" defaults. Notebooks and tests supply their own parameter sets explicitly. Literature-grounded starters live in `docs/PARAMETER_SOURCES.md`.
