# Parameter Sources

Literature-grounded starter parameters for the Layer-1 DGP (`synthetic/want/ou_with_noise`), documented in the reference notebook `notebooks/00_dgp_design.ipynb` and used by the Layer-1 prototype.

**Scope caveat up front.** Direct empirical studies on **intraday EUR 50Y IRS microstructure** are essentially nonexistent in the open academic literature — this tenor trades OTC and in professional feeds; academics rarely have the data. Every value below extrapolates from adjacent markets (10Y US Treasuries on BrokerTec, German bond futures on Eurex, equity pairs, FX). Confidence is tagged per parameter.

The purpose of these parameters is to produce **qualitatively realistic** intraday paths so that RV/BV signature-plot analysis has something to detect. They are not a calibration of the real 50Y EUR IRS market. If any downstream result is sensitive to a +/-2x change in any of these, that is a fragility worth documenting before relying on empirical Excel data.

## Evidence tiers

Each concrete claim below is tagged:

- **[V]** — *verified:* directly supported by the cited paper.
- **[A]** — *author extrapolation:* plausible but not directly supported by the cited paper; my scaling judgment from adjacent-market evidence.

Only **[V]** claims should be reused by you or your supervisor without re-reading the source.

---

## Summary

| Parameter   | Value         | Meaning                                 | Confidence     |
|-------------|---------------|-----------------------------------------|----------------|
| `μ`         | `0.028`       | ≈ 2.8% — representative 50Y EUR level   | Easy to adjust |
| `θ`         | `ln(2)/60`    | Mean-reversion speed; half-life 60 min  | Low            |
| `σ_eff`     | `3.8e-5`      | Per-√minute vol (≈ 0.38 bp / √min)      | Medium         |
| `σ_noise`   | `1.5e-5`      | Microstructure noise SD (≈ 0.15 bp)     | Medium-low     |

Derived properties:
- Stationary SD around `μ`: ≈ 2.5 bp.
- Typical intraday peak-to-trough range: ≈ 5–10 bp.
- Brownian-equivalent envelope without mean-reversion over a 540-min session: ≈ 8.8 bp. Mean-reversion compresses this by ~3.5×.

---

## 1. Mean-reversion half-life — 60 min

**What the literature says.**
- **[V]** None of the canonical fixed-income RV papers (Andersen-Bollerslev-Diebold-Labys; Fleming-Remolona; Bandi-Russell) estimates an OU half-life on the efficient rate itself at the intraday scale. The efficient log-price is treated as a (semi)martingale with no intraday drift; mean-reversion in rates is a lower-frequency phenomenon in Vasicek / CIR-style models.
- **[V]** Microstructure-induced negative autocorrelation at the first return lag (bid-ask bounce) is documented in Poutré-Ragel-Cont (2024) for German bond futures and in Fleming-Remolona for US Treasuries — but this is noise-driven mean reversion, not signal mean reversion.
- **[A]** The 30–120 min defensible band for intraday half-lives in less-liquid long-tenor swaps is my extrapolation from the equity-pairs / Holý-Tomanová literature, which finds half-lives from ~5 min (highly liquid pairs) to several hours. I do not have a 50Y-IRS-specific citation.

**Chosen value: 60 min (middle of band).** Confidence: **low** — this is extrapolation, not a number from any paper. Sensitivity of downstream results to this choice should be tested explicitly.

## 2. Stationary SD around μ — 2.5 bp

**What the literature says.**
- **[V]** The MOVE index decomposition implies daily US Treasury bp-vol of ~6 bp/day close-to-close at a MOVE of ~100 (normal regime ≈ 5–8 bp/day for 10Y UST). Sources: Convexity Maven "RateLab", Schwab MOVE explainer.
- **[A]** Long-dated swap rates (30Y+) showing "70–85% of 10Y vol" is rule-of-thumb desk knowledge; I have not located a specific paper that quotes this ratio. Treat as author scaling judgment.
- **[A]** Mapping daily bp-vol to an OU stationary SD by taking "roughly half" is a modeller's choice; no literature formalises this.

**Chosen value: 2.5 bp stationary SD.** Confidence: **medium** on the daily bp-vol anchor (MOVE-implied, well-known); **low** on the daily-to-stationary mapping.

### 2a. Derivation of `σ_eff`

For an Ornstein-Uhlenbeck process, the stationary standard deviation is `s = σ_eff / √(2θ)`. Rearranging, with `s = 2.5e-4` (decimal) and `θ = ln(2)/60 ≈ 0.01155 min⁻¹`:

```
σ_eff = s · √(2θ) = 2.5e-4 · √(0.02310) ≈ 2.5e-4 · 0.1520 ≈ 3.80e-5
```

per √minute (≈ 0.38 bp per √minute).

## 3. Noise-to-signal variance ratio — ≈ 0.25 at 1-min

**What the literature says.**
- **[V]** Hansen & Lunde (2006) formalise the noise-variance estimator `ω² = RV/(2n)` for equities.
- **[V]** Aït-Sahalia & Yu (2009) estimate noise-to-signal ratios for NYSE equities. (The specific "~63% of noise variance explained by the bid-ask spread" figure is my recollection rather than a quoted equation from that paper — treat as unverified.)
- **[V]** Chaboud et al. (Fed IFDP 905, 2007) find that for 10Y UST on BrokerTec, the critical sampling interval beyond which microstructure noise dominates RV estimation is **2–3 minutes on non-announcement days**, ~40 seconds on announcement days with realized-kernel estimators.
- **[A]** The specific "1–10% of return variance at 1-min" figure for 10Y UST is my extrapolation from the 2–3 min break-point result — Chaboud et al. discuss the issue qualitatively; a reader wanting this exact ratio should compute it from their paper's tables rather than cite my doc.
- **[A]** The "scale up 3–10×" for 50Y EUR IRS relative to 10Y UST is judgment: 50Y is dealer-quote-driven, less liquid, with longer duration amplifying quote-midpoint noise.

**Chosen ratio: 0.25 (middle of the scaled band).**

### 3a. Derivation of `σ_noise`

Noise contributes `2·σ_noise²` to the 1-min return variance (because returns difference the noise). Setting that equal to `0.25 · σ_eff²`:

```
σ_noise = σ_eff · √(0.25 / 2) ≈ 3.8e-5 · 0.354 ≈ 1.35e-5 → rounded to 1.5e-5
```

**Approximation note.** The expression above uses the *small-θ* approximation that the 1-min efficient return variance equals `σ_eff²` (i.e., returns are Brownian over one minute). The exact 1-min efficient return variance for a stationary OU process is `σ_eff² · (1 − exp(−θ))/θ`. At our `θ ≈ 0.01155`, the factor `(1 − exp(−θ))/θ ≈ 0.9942`, so the approximation error is **~0.6%** — negligible. The approximation would break down for very large θ (short half-lives).

Confidence: **medium-low** on the ratio itself — the 10Y UST evidence is real but the 50Y scaling is judgment.

## 4. Signature-plot break point — not a DGP parameter, a design check

- **[V]** Chaboud et al. (Fed IFDP 905): critical sampling interval 2–3 min for 10Y UST on BrokerTec (non-announcement days).
- **[V]** Hansen & Lunde (2006): canonical 4–5 min "sweet spot" for RV estimation in FX and bonds.
- **[V]** Poutré-Ragel-Cont (2024): German bond futures show the familiar decreasing-RV signature plot. They report signature-plot behaviour for Schatz / Bobl / Bund / Buxl futures; the specific statement that *Buxl shows the largest tick-noise contamination* is my interpretation of their plots, not a direct quote — verify against the paper if material.
- **[A]** For 50Y EUR IRS (less liquid than even Buxl), shift the break to ~5–10 min.

**Validation of our candle grid.** The Layer-1 prototype uses `Δ ∈ {5, 15, 30, 60, 120}` min. Against a break of ~5–10 min, 5-min should still be noise-contaminated and 15-min+ should be in the flat regime — the signature plot **should visibly flatten between 5 and 15 min** if the DGP is roughly calibrated. Note: the grid cannot resolve a break at 10 min exactly. Consider adding a 10-min diagnostic point in the live Layer-1 snippet.

---

## Assumptions embedded in the current DGP

These are **modelling choices baked into the code**, not just data-fitting choices. Flag them in any downstream analysis.

1. **Efficient price starts at μ.** Both OU-based DGPs initialise `X₀ = μ` rather than drawing from the stationary distribution `N(μ, σ_eff²/(2θ))`. This suppresses early-session dispersion and bakes in *no opening dislocation*. For the delayed-close thesis — which is about intraday deviations from fair value — this is a conservative simplification. Revisit if we ever want to model sessions where the 11:00 close is executed when the rate is already far from equilibrium.
2. **σ_noise derivation uses the small-θ approximation.** Valid at our θ (~0.6% error); would need the exact form `(1 − exp(−θ))/θ` factor for short half-lives.
3. **No time-of-day volatility envelope.** Real intraday vol is heteroskedastic — typically higher around London open, ECB-related hours, and US macro releases. This DGP produces stationary vol across the session.
4. **No jumps.** Real markets have announcement jumps. BV's robustness to jumps is one reason we include it, but this DGP will not exercise that property. Add jumps if a method turns out to be sensitive to them.
5. **Stationary μ, not drifting.** `μ` is constant by construction. Real intraday means drift with news flow.
6. **Single-session scope.** No cross-session carryover or overnight gap modelling.

---

## References

- Hansen, P. R., & Lunde, A. (2006). [Realized Variance and Market Microstructure Noise](https://web-docs.stern.nyu.edu/salomon/docs/Hansen-Lunde.pdf). *Journal of Business & Economic Statistics.*
- Chaboud, A., Chiquoine, B., Hjalmarsson, E., & Loretan, M. (2007). [Frequency of Observation and the Estimation of Integrated Volatility in Deep and Liquid Financial Markets](https://www.federalreserve.gov/econres/ifdp/frequency-of-observation-and-the-estimation-of-integrated-volatility-in-deep-and-liquid-financial-markets.htm). *Federal Reserve Board IFDP 905.*
- Aït-Sahalia, Y., & Yu, J. (2009). [High Frequency Market Microstructure Noise Estimates and Liquidity Measures](https://www.princeton.edu/~yacine/liquidity.pdf). *Annals of Applied Statistics.*
- Fleming, M. J., & Remolona, E. M. (1999). [Price Formation and Liquidity in the US Treasury Market: The Response to Public Information](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=152708). *Journal of Finance.*
- Mizrach, B., & Neely, C. J. (2009). [The Microstructure of the US Treasury Market](https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr381.pdf). *FRBNY Staff Report 381.*
- Poutré, A., Ragel, F., & Cont, R. (2024). [Stylized Facts of the German Bond Futures Market](https://arxiv.org/html/2401.10722v1). *arXiv:2401.10722.*
- Holý, V., & Tomanová, P. (2018). [Estimation of Ornstein-Uhlenbeck Process under Microstructure Noise](https://arxiv.org/abs/1811.09312). *arXiv:1811.09312.*
- Andersen, T. G., & Bollerslev, T. (1997). [Intraday Periodicity and Volatility Persistence in Financial Markets](https://public.econ.duke.edu/~boller/Published_Papers/joef_00.pdf). *Journal of Empirical Finance.*
- ECB (2005). [Term Structure of Implied Interest Rate Volatilities](https://www.ecb.europa.eu/pub/pdf/other/mb200512_focus02.en.pdf). *ECB Monthly Bulletin, December 2005.*
