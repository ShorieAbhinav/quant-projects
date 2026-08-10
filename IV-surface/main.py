import numpy as np

from alpaca_data import build_market_price_grid
from vol_surface import build_implied_vol_grid, fit_spline, reprice_and_check
from plots import plot_3d_surface, plot_smile, plot_term_structure

SYMBOL = "AAPL"
r = 0.05    # approximate risk-free rate
q = 0.005   # approximate AAPL dividend yield


def main():
    # 1) Pull real market call prices from Alpaca (rectangular strike x maturity grid)
    S0, strikes, maturities, market_prices = build_market_price_grid(
    SYMBOL, n_expirations=4, min_days_out=3, moneyness_band=(0.95, 1.05)
)

    print(f"Spot ({SYMBOL}): {S0:.2f}")
    print(f"Strikes used ({len(strikes)}): {strikes}")
    print(f"Maturities (years): {np.round(maturities, 4)}")
    print("\nMarket call prices C_mkt(K,T):")
    print(market_prices.round(4))

    # 2) Solve implied volatility at every grid point
    implied_surface = build_implied_vol_grid(S0, strikes, maturities, market_prices, r, q=q)
    print("\nImplied vol surface recovered from prices (percent):")
    print((implied_surface * 100).round(4))

    # 3) Fit a smooth bicubic spline over (moneyness, maturity)
    spline = fit_spline(S0, strikes, maturities, implied_surface, smoothing=0.0)

    # 4) Sanity check: repricing with solved vols should reproduce market prices
    abs_price_err = reprice_and_check(S0, strikes, maturities, implied_surface, market_prices, r, q=q)
    print("\nMax absolute repricing error:", float(abs_price_err.max().max()))

    # 5) Plots
    # 5) Plots
    fig_surface = plot_3d_surface(SYMBOL, S0, strikes, maturities, implied_surface, spline)
    fig_surface.show()

    fig_smile = plot_smile(SYMBOL, S0, implied_surface)
    fig_smile.show()

    fig_term = plot_term_structure(SYMBOL, S0, implied_surface)
    fig_term.show()

    # 6) Export
    market_prices.to_csv("market_call_prices.csv")
    implied_surface.to_csv("implied_vol_surface.csv")
    print("\nSaved: market_call_prices.csv")
    print("Saved: implied_vol_surface.csv")


if __name__ == "__main__":
    main()
