# backend/core/analytics.py
import numpy as np
import pandas as pd
from statsmodels.regression.linear_model import OLS
from statsmodels.tsa.stattools import adfuller

def hedge_ratio_ols(y: pd.Series, x: pd.Series):
    """OLS hedge ratio (beta) for y ~ beta*x + c"""
    df = pd.concat([x, y], axis=1).dropna()
    if len(df) < 2:
        return np.nan
    X = df.iloc[:, 0].values
    Y = df.iloc[:, 1].values
    Xmat = np.vstack([X, np.ones(len(X))]).T
    model = OLS(Y, Xmat).fit()
    beta = model.params[0]
    return float(beta)

def compute_spread(y: pd.Series, x: pd.Series, hedge_ratio: float):
    return y - hedge_ratio * x

def rolling_hedge_ratio(y: pd.Series, x: pd.Series, window: int = 60):
    """Return a Series of hedge ratios computed on rolling windows."""
    def _win(v):
        # v contains interleaved x,y columns when applied with rolling apply
        half = int(len(v) / 2)
        x_win = pd.Series(v[:half])
        y_win = pd.Series(v[half:])
        return hedge_ratio_ols(y_win, x_win)
    stacked = pd.concat([x, y], axis=1).dropna()
    if len(stacked) < window:
        return pd.Series([np.nan]*len(stacked), index=stacked.index)
    # sliding by applying on values: (slower but simple). We'll return aligned to right edge.
    out = stacked.rolling(window=window).apply(
        lambda arr: hedge_ratio_ols(pd.Series(arr[:,1]), pd.Series(arr[:,0])),
        raw=True
    )
    # out is DataFrame shaped; first column contains the result (since apply applied to both cols)
    # Extract first column
    if hasattr(out, 'iloc'):
        return out.iloc[:, 0]
    return out

def compute_zscore(series: pd.Series, window: int = 60):
    m = series.rolling(window=window).mean()
    s = series.rolling(window=window).std(ddof=0)
    z = (series - m) / s
    return z

def rolling_corr(s1: pd.Series, s2: pd.Series, window: int = 60):
    return s1.rolling(window=window).corr(s2)

def adf_test(series: pd.Series):
    s = series.dropna()
    if len(s) < 10:
        return {'stat': None, 'pvalue': None, 'nobs': len(s)}
    res = adfuller(s, autolag='AIC')
    return {'stat': float(res[0]), 'pvalue': float(res[1]), 'usedlag': int(res[2]), 'nobs': int(res[3])}
