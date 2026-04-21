# Parameter Sources

Literature-grounded starter parameters for the Layer-1 DGP (`synthetic/want/ou_with_noise`), applied in `notebooks/00_granularity_selection.ipynb`.

**Scope caveat up front.** Direct empirical studies on **intraday EUR 50Y IRS microstructure** are essentially nonexistent in the open academic literature — this tenor trades OTC and in professional feeds; academics rarely have the data. Every value below extrapolates from adjacent markets (10Y US Treasuries on BrokerTec, German bond futures on Eurex, equity pairs, FX). Confidence is tagged per parameter.

The purpose of these parameters is to produce **qualitatively realistic** intraday paths so that RV/BV signature-plot analysis has something to detect. They are not a calibration of the real 50Y EUR IRS market. If any downstream result is sensitive to a ±2× change in any of these, that is a fragility worth documenting before touching real bQuant data.

---

## Summary

| Parameter    | Value        | Meaning                               | Confidence   |
|--------------|--------------|---------------------------------------|--------------|
| `μ`          | `0.028`      | ≈ 2.8% — representative 50Y EUR level | Easy to adjust |
| `θ`          | `ln(2)/60`   | Mean-reversion speed; half-life 60 min| Low          |
| `σ_eff`      | `3.8e-5`     | Per-√minute vol (≈ 0.38 bp / √min)    | Medium       |
| `σ_noise`    | `1.5e-5`     | Microstructure noise SD (≈ 0.15 bp)   | Medium-low   |

Derived properties:
- Stationary SD around `μ`: ≈ 2.5 bp.
- Typical intraday peak-to-trough range: ≈ 5–10 bp.
- Brownian-equivalent envelope without mean-reversion over a 540-min session: ≈ 8.8 bp. Mean-reversion compresses this by ~3.5×.

---

## 1. Mean-reversion half-life — 60 min

**What the literature says.** None of the canonical fixed-income RV papers (Andersen-Bollerslev-Diebold-Labys; Fleming-Remolona; Bandi-Russell) estimate an OU half-life on the efficient rate itself at the intraday scale. The efficient log-price is typically treated as a (semi)martingale with no intraday drift — mean reversion in rates is a lower-frequency phenomenon in Vasicek / CIR-style models. What *does* show up at intraday frequency is microstructure-induced negative autocorrelation at the first lag (bid-ask bounce), documented in Poutré-Ragel-Cont (2024) for German bond futures and in Fleming-Remolona for US Treasuries — this is noise-driven mean reversion, not signal mean reversion.

For transient deviations from an intraday fair value (the object of our stat-arb thesis), empirical work on equity pairs and the Holý-Tomanová OU-under-noise estimator finds intraday half-lives ranging from ~5 minutes (highly liquid pairs) to several hours. For a less liquid long-tenor swap, **30–120 minutes is a defensible band**.

**Chosen value: 60 min (middle of band).** Confidence: **low** — this is extrapolation, not a number from the literature. Sensitivity of downstream results to this choice should be tested explicitly.

## 2. Stationary SD around μ — 2.5 bp

**What the literature says.** The MOVE index decomposition implies daily US Treasury bp-vol of ~6 bp/day close-to-close at a MOVE of ~100 (normal regime is 5–8 bp/day for 10Y UST). Long-dated swap rates (30Y+) typically show lower bp-vol than 10Y, empirically ~70–85% of 10Y vol — so 50Y EUR IRS daily bp-vol plausibly sits in the **4–7 bp/day** range.

The OU *stationary* SD is what the rate wiggles within during a session, not what it drifts by across sessions. A reasonable choice is roughly half the daily bp-vol — giving **2.5 bp**.

**Derivation of `σ_eff`.** Given stationary SD `s = 2.5e-4` (decimal) and `θ = ln(2)/60 ≈ 0.01155 min⁻¹`:

```
σ_eff = s · √(2θ) = 2.5e-4 · √(0.0231) ≈ 3.8e-5
```

per √minute. (Equivalent: ≈ 0.38 bp per √minute.)

Confidence: **medium** on daily bp-vol from MOVE-implied sources; **low** on the daily-to-stationary mapping (modeller's judgment).

## 3. Noise-to-signal variance ratio — ≈ 0.25 at 1-min

**What the literature says.** Hansen & Lunde (2006) formalise the noise-variance estimator `ω² = RV/(2n)`. Aït-Sahalia & Yu estimate noise-to-signal ratios for NYSE equities, where the bid-ask spread explains roughly 63% of noise variance. The Fed IFDP 905 paper gives the most bond-relevant number: for 10Y UST on BrokerTec, 1-minute sampling is already in the "mildly contaminated" rather than "noise-dominated" regime — noise variance is typically 1–10% of true return variance per sampled interval.

For a less liquid instrument like 50Y EUR IRS — dealer-quote-driven, lower trade frequency, duration amplifying quote-midpoint errors — scale up by 3–10× to give **0.10–0.50**.

**Chosen ratio: 0.25 (middle of scaled band).**

**Derivation of `σ_noise`.** Noise contributes `2·σ_noise²` to the 1-min return variance (because returns difference the noise). Setting that equal to `0.25 · σ_eff²`:

```
σ_noise = σ_eff · √(0.25 / 2) ≈ 3.8e-5 · 0.354 ≈ 1.35e-5 → rounded to 1.5e-5
```

Confidence: **medium-low** — the 10Y UST anchor is solid; the scaling factor to 50Y EUR IRS is judgment.

## 4. Signature-plot break point — not a DGP parameter, but a design validation

**What the literature says.** The Fed IFDP 905 paper directly answers this for 10Y UST: critical sampling interval **2–3 minutes** on non-announcement days, down to 40 seconds on announcement days (with realized-kernel estimators). Hansen & Lunde place the canonical "4–5 minute sweet spot" for FX and bonds. Poutré-Ragel-Cont show the familiar decreasing-RV signature-plot profile across German bond futures, with the Buxl (24–35Y) — closest in duration to 50Y EUR IRS — showing the largest tick-noise contamination.

For a less-liquid 50Y swap, the break should shift up to roughly **5–10 min**.

**Validation of our candle grid.** The notebook uses `Δ ∈ {5, 15, 30, 60, 120}` min. This straddles the break point perfectly: 5-min should still be noise-contaminated (RV visibly inflated relative to BV), 15-min onwards should be in the flat regime. If our DGP is calibrated anywhere close to reality, the signature plot **will flatten between 5 and 15 min** — exactly the diagnostic the notebook is designed to produce.

---

## Known limitations

- **50Y EUR IRS is not 10Y UST.** Lower trade frequency, dealer-quote-driven price discovery, longer duration amplifying quote-midpoint noise. Real noise may be larger than estimated here.
- **No time-of-day vol envelope.** Real intraday vol is heteroskedastic — typically higher around London open, ECB-related hours, and around US macro releases. This DGP produces stationary vol across the session. Good enough for signature-plot testing; not good enough for backtest-realistic path generation.
- **No jumps.** Real markets have announcement jumps. BV's robustness to jumps is one reason we include it, but this DGP will not exercise that property. Add jumps if a method turns out to be sensitive to them.
- **Stationary OU, not drifting.** `μ` is constant by construction. Real intraday means drift with overnight news flow.

---

## References

- Hansen, P. R., & Lunde, A. (2006). [Realized Variance and Market Microstructure Noise](https://web-docs.stern.nyu.edu/salomon/docs/Hansen-Lunde.pdf). *Journal of Business & Economic Statistics.*
- Chaboud, A., Chiquoine, B., Hjalmarsson, E., & Loretan, M. (2007). [Frequency of Observation and Estimation of Integrated Volatility in Deep and Liquid Markets](https://www.federalreserve.gov/pubs/ifdp/2007/905/ifdp905.htm). *Federal Reserve Board IFDP 905.*
- Aït-Sahalia, Y., & Yu, J. (2009). [High Frequency Market Microstructure Noise Estimates and Liquidity Measures](https://www.princeton.edu/~yacine/liquidity.pdf). *Annals of Applied Statistics.*
- Fleming, M. J., & Remolona, E. M. (1999). [Price Formation and Liquidity in the US Treasury Market: The Response to Public Information](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=152708). *Journal of Finance.*
- Mizrach, B., & Neely, C. J. (2009). [The Microstructure of the US Treasury Market](https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr381.pdf). *FRBNY Staff Report 381.*
- Poutré, A., Ragel, F., & Cont, R. (2024). [Stylized Facts of the German Bond Futures Market](https://arxiv.org/html/2401.10722v1). *arXiv:2401.10722.*
- Holý, V., & Tomanová, P. (2018). [Estimation of Ornstein-Uhlenbeck Process under Microstructure Noise](https://arxiv.org/abs/1811.09312). *arXiv:1811.09312.*
- Andersen, T. G., & Bollerslev, T. (1997). [Intraday Periodicity and Volatility Persistence in Financial Markets](https://public.econ.duke.edu/~boller/Published_Papers/joef_00.pdf). *Journal of Empirical Finance.*
- ECB (2005). [Term Structure of Implied Interest Rate Volatilities](https://www.ecb.europa.eu/pub/pdf/other/mb200512_focus02.en.pdf). *ECB Monthly Bulletin, December 2005.*
