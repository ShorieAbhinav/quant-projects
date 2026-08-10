import numpy as np

from black_scholes import black_scholes_call


def implied_vol_bisection(
    C_mkt: float,
    S0: float,
    K: float,
    T: float,
    r: float,
    q: float = 0.0,
    sigma_low: float = 1e-8,
    sigma_high: float = 2.0,
    tol: float = 1e-12,
    max_iter: int = 250,
) -> float:
    """
    Robust implied volatility solver using bisection.
    Returns NaN if a root cannot be bracketed.
    """
    if T <= 0.0:
        return np.nan

    C_mkt = float(C_mkt)

    def f(sig: float) -> float:
        return black_scholes_call(S0, K, T, r, sig, q=q) - C_mkt

    lo = float(sigma_low)
    hi = float(sigma_high)
    f_lo = f(lo)
    f_hi = f(hi)

    # Expand hi until we bracket a sign change or give up
    tries = 0
    while f_lo * f_hi > 0.0 and tries < 25:
        hi *= 1.5
        f_hi = f(hi)
        tries += 1

    if f_lo * f_hi > 0.0:
        return np.nan

    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        f_mid = f(mid)

        if abs(f_mid) < tol or (hi - lo) < tol:
            return float(mid)

        if f_lo * f_mid <= 0.0:
            hi = mid
            f_hi = f_mid
        else:
            lo = mid
            f_lo = f_mid

    return float(mid)
