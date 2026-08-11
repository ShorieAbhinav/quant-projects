# Implied Volatility Surface Engine

A Python project that pulls live options data from Alpaca's API, prices options
using a hand built Black-Scholes model, solves for implied volatility numerically,
and renders the result as an interactive 3D volatility surface.

Built to calculate everything from scratch rather than relying on a library that
hands you implied volatility directly.

## What it does

1. **Pulls real market data** from Alpaca (option contracts, live quotes, and
   historical bars as a fallback for illiquid strikes) rather than a static or
   pre packaged dataset.
2. **Prices options** using a Black-Scholes implementation written from the
   formula, with support for a continuous dividend yield.
3. **Solves implied volatility** for every strike and maturity in the grid,
   using a bisection root finder.
4. **Fits a smooth surface** with a bicubic spline across strike and maturity.
5. **Visualizes the result** two ways: a static interactive Plotly figure
   (`main.py`), and a live updating matplotlib version that polls the market
   on a timer (`live_surface.py`).

As a sanity check, repricing every contract with its solved implied volatility
reproduces the original market price to within `1e-12`, confirming the pricer
and the solver are mathematically consistent with each other.

## Project structure

```
IV-surface/
  alpaca_data.py     # Alpaca data pulling: contracts, quotes, historical bars,
                      # and the rectangular strike x maturity grid builder
  black_scholes.py    # Black-Scholes call pricer
  implied_vol.py       # Bisection implied volatility solver
  vol_surface.py       # Implied vol grid + bicubic spline fit + repricing check
  plots.py              # Plotly figures: 3D surface, smile, term structure
  main.py                 # One shot pipeline: pull data, solve, plot, export CSVs
  live_surface.py           # Live polling version with a matplotlib UI
  app.py                     # Dash web dashboard (in progress, see below)
  requirements.txt
  .env.example
```

## Setup

1. Clone the repo and `cd` into `IV-surface`.
2. Create a virtual environment and install dependencies:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and fill in your own Alpaca API keys:
   ```
   ALPACA_API_KEY=your_key_here
   ALPACA_SECRET_KEY=your_secret_here
   ```
   Keys work with either a paper or live Alpaca account; the project only
   reads market data, it never places trades.

## Running it

**One shot version**, pulls data once and shows three plots (3D surface, smile,
term structure), then saves the price and implied vol grids to CSV:
```bash
python main.py
```

**Live version**, polls the market every 5 seconds and redraws a dark themed,
spline smoothed 3D surface (raw solved points overlaid as markers) with a
front month skew panel, with a lock button to freeze the view:
```bash
python live_surface.py
```

## Dashboard (in progress)

A Dash web dashboard (`app.py`) is in development: symbol picker, auto-refresh,
the same 3D surface / smile / term structure plots rendered in-browser, and a
live price table. Core pieces work, but it's not yet a finished, polished
release -- expect rough edges. To try it:
```bash
python app.py
```
then open the local URL it prints (defaults to `http://127.0.0.1:8050`).

## Notes on data quality

Options liquidity varies a lot by strike and time of day. Far from the money
strikes may not have traded recently, so `build_market_price_grid` automatically
retries with progressively wider search parameters (tighter near the money bands
first) until it finds enough strikes with usable data, rather than failing on
the first attempt. When the market is closed, prices fall back to the last
close or a recent historical bar rather than a live quote, which can introduce
a small timing mismatch between the option price and the spot price used.
