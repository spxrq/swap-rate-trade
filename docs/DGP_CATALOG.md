# DGP Catalog

## `synthetic/want/` — thesis-matching DGPs

| Name | File | Description | Parameters | Status |
|------|------|-------------|------------|--------|
| OU + microstructure noise | `want/ou_with_noise.py` | Ornstein–Uhlenbeck efficient price mean-reverting to `μ` with half-life `ln(2)/θ`, plus iid Gaussian microstructure noise. Supports both Layer-1 (microstructure detection via RV/BV) and Layer-2 (mean-reversion detection) analysis. | `μ`, `θ`, `σ_eff`, `σ_noise`, `n_minutes`, `start`, `seed` | Scaffolded; literature-grounded starter parameters in `PARAMETER_SOURCES.md` |

## `synthetic/dont_want/` — adversarial / null DGPs

| Name | File | Description | Negates | Parameters | Status |
|------|------|-------------|---------|------------|--------|
| Random walk + noise | `dont_want/random_walk_with_noise.py` | Random-walk efficient price plus iid Gaussian microstructure noise. | Mean-reversion | `start_level`, `σ_eff`, `σ_noise`, `n_minutes`, `start`, `seed` | Scaffolded |
| OU, no noise | `dont_want/ou_no_noise.py` | Pure OU efficient price; no microstructure noise overlay. Useful as a design diagnostic, but not a clean flat-signature null under level-space non-overlapping RV because OU mean reversion can make RV decline with Δ. | Microstructure noise | `μ`, `θ`, `σ_eff`, `n_minutes`, `start`, `seed` | Scaffolded; null interpretation under review |

## Validation principle

A method is accepted only when **both** Monte Carlo criteria hold across many simulated paths. Per-path comparison is unsound: null DGPs are stochastic, and a properly-sized α-level test will falsely reject at rate α by construction.

**Baseline:** N = 500 paths, α = 0.05, β = 0.9, FPR tolerance = 1.5·α.

1. **Power on `want/ou_with_noise`** — over N paths, the method must detect the property (mean-reversion at the chosen Δ*; microstructure noise at fine Δ) with frequency ≥ β.
2. **Type-I control on `dont_want/random_walk_with_noise`** — over N paths, the method must falsely detect mean-reversion with frequency ≤ 1.5·α.
3. **Type-I control on `dont_want/ou_no_noise` or replacement no-noise null** — over N paths, the method must falsely detect microstructure noise with frequency ≤ 1.5·α. The current OU-no-noise DGP is under review as a flat-signature benchmark because no-noise OU dynamics can still generate a declining RV curve across Δ.

## Conventions

- Every DGP function uses keyword-only arguments. No positional params.
- Every DGP accepts a `seed` for reproducibility.
- Every DGP returns a DataFrame conforming to `DATA_CONTRACT.md`.
- Every DGP has at least one test in `tests/` that verifies its claimed statistical property.
- DGP function signatures have no hard-coded "realistic" defaults. Notebooks and tests supply their own parameter sets explicitly. Literature-grounded starters live in `docs/PARAMETER_SOURCES.md`.
