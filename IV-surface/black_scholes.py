import numpy as np
from scipy.stats import norm


def black_scholes_call(S0: float, K: float, T: float, r: float, sigma: float, q: float = 0.0) -> float:
    """
    Black-Scholes European call with continuous dividend yield.

    Inputs
    - S0: spot price
    - K: strike
    - T: time to maturity (years)
    - r: risk-free rate
    - q: dividend yield
    - sigma: volatility

    Output
    - Call price
    """
    if T <= 0.0:
        return max(S0 - K, 0.0)

    # Numerical guard: sigma must be positive
    sigma = max(float(sigma), 1e-12)

    sigma_sqrt_T = sigma * np.sqrt(T)
    d1 = (np.log(S0 / K) + (r - q + 0.5 * sigma * sigma) * T) / sigma_sqrt_T
    d2 = d1 - sigma_sqrt_T

    discounted_spot = S0 * np.exp(-q * T)
    discounted_strike = K * np.exp(-r * T)

    option_price = float(discounted_spot * norm.cdf(d1) - discounted_strike * norm.cdf(d2))
    return option_price
