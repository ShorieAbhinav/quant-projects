import numpy as np
import pandas as pd
from scipy.interpolate import RectBivariateSpline

from implied_vol import implied_vol_bisection


def build_implied_vol_grid(S0, strikes, maturities, market_prices, r, q=0.0):
    """Solve implied vol at every (strike, maturity) cell in market_prices."""
    implied_surface = pd.DataFrame(index=strikes, columns=maturities, dtype=float)

    for K in strikes:
        for T in maturities:
            implied_surface.loc[K, T] = implied_vol_bisection(
                C_mkt=float(market_prices.loc[K, T]),
                S0=S0, K=float(K), T=float(T),
                r=r, q=q,
            )

    return implied_surface


def fit_spline(S0, strikes, maturities, implied_surface, smoothing=0.0):
    """
    Fit a bicubic spline over (moneyness, maturity) -> implied vol.

    RectBivariateSpline requires more grid points than the spline degree in
    each direction (kx, ky). With few maturities or strikes (e.g. only 3
    expirations after the auto-retry logic picked a tight band), a cubic
    (degree 3) spline isn't possible -- so the degree is lowered automatically
    to fit what the grid actually has.
    """
    moneyness = (strikes / S0).astype(float)
    Z_grid = implied_surface.to_numpy(dtype=float)  # shape (len(moneyness), len(maturities))

    kx = min(3, len(moneyness) - 1)
    ky = min(3, len(maturities) - 1)
    if kx < 1 or ky < 1:
        raise ValueError(
            f"Not enough grid points to fit a spline: {len(moneyness)} strikes, "
            f"{len(maturities)} maturities. Need at least 2 of each."
        )

    spline = RectBivariateSpline(moneyness, maturities, Z_grid, kx=kx, ky=ky, s=smoothing)
    return spline


def reprice_and_check(S0, strikes, maturities, implied_surface, market_prices, r, q=0.0):
    """Sanity check: repricing with the solved implied vols should reproduce market_prices."""
    repriced = pd.DataFrame(index=strikes, columns=maturities, dtype=float)

    from black_scholes import black_scholes_call

    for K in strikes:
        for T in maturities:
            sig = float(implied_surface.loc[K, T])
            repriced.loc[K, T] = black_scholes_call(S0, float(K), float(T), r, sig, q=q)

    abs_price_err = (repriced - market_prices).abs()
    return abs_price_err
