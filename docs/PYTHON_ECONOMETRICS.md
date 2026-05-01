# Python Econometrics Stack

The project can use the full local Python time-series and econometrics stack. There is no platform allowlist constraint.

## Core Libraries

| Library | Use |
|---------|-----|
| numpy | numerical arrays and vectorized calculations |
| pandas | DataFrame loading, timestamp handling, resampling, summaries |
| matplotlib | plots |
| scipy | statistical utilities |
| statsmodels | ACF/PACF, AR/AutoReg, ADF, KPSS, Ljung-Box, Breusch-Godfrey, Breusch-Pagan, HAC covariance |
| arch | later GARCH, EGARCH, TGARCH/GJR-GARCH volatility modelling |
| jupyter/jupyterlab | notebook execution |

## Modelling Direction

1. Use RV/BV to choose a working granularity.
2. Use ACF/PACF on levels, changes, and squared changes.
3. Fit AR/AutoReg specifications to the 5m level.
4. Use ADF and KPSS together for stationarity evidence.
5. Use Ljung-Box and Breusch-Godfrey for residual serial correlation.
6. Use Breusch-Pagan and ARCH LM for heteroskedasticity/volatility clustering.
7. If volatility clustering is material, move to `arch` models: GARCH, EGARCH, and asymmetric GJR-GARCH/TGARCH-style specifications.
