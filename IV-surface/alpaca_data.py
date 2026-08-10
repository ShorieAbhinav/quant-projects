import os
from collections import defaultdict
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd
from dotenv import load_dotenv

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetOptionContractsRequest
from alpaca.data.historical.option import OptionHistoricalDataClient
from alpaca.data.historical.stock import StockHistoricalDataClient
from alpaca.data.requests import OptionLatestQuoteRequest, StockLatestQuoteRequest, OptionBarsRequest
from alpaca.data.timeframe import TimeFrame

load_dotenv()
API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

trading_client = TradingClient(API_KEY, SECRET_KEY, paper=False)
option_data_client = OptionHistoricalDataClient(API_KEY, SECRET_KEY)
stock_data_client = StockHistoricalDataClient(API_KEY, SECRET_KEY)


def get_spot_price(symbol: str) -> float:
    """Current stock price, using mid of bid/ask, falling back to whichever side is nonzero."""
    req = StockLatestQuoteRequest(symbol_or_symbols=symbol)
    q = stock_data_client.get_stock_latest_quote(req)[symbol]
    bid, ask = q.bid_price, q.ask_price
    if bid and ask:
        return (bid + ask) / 2.0
    return bid or ask


def get_call_contracts(symbol: str, min_days_out=3):
    """
    All active call contracts for a symbol, expiring at least min_days_out from today.
    Paginates through all pages, since Alpaca returns contracts nearest-expiration-first
    and a single page would otherwise only surface the closest few expirations.

    Returns
    - strikes_by_expiry: dict of expiration_date -> set of strikes
    - lookup: dict of (expiration_date, strike) -> (occ_symbol, close_price)
    """
    min_expiration = date.today() + timedelta(days=min_days_out)

    strikes_by_expiry = defaultdict(set)
    lookup = {}
    page_token = None

    while True:
        req = GetOptionContractsRequest(
            underlying_symbols=[symbol],
            status="active",
            type="call",
            expiration_date_gte=min_expiration,
            page_token=page_token,
        )
        response = trading_client.get_option_contracts(req)

        for c in response.option_contracts:
            strikes_by_expiry[c.expiration_date].add(c.strike_price)
            close = float(c.close_price) if c.close_price is not None else None
            lookup[(c.expiration_date, c.strike_price)] = (c.symbol, close)

        page_token = response.next_page_token
        if not page_token:
            break

    return strikes_by_expiry, lookup


def pick_expirations_and_strikes(strikes_by_expiry, min_days_out=3, n_expirations=6,
                                  moneyness_band=(0.80, 1.20), spot=None):
    """
    Take the nearest N expirations already filtered by get_call_contracts, then
    intersect their strikes so every chosen strike exists at every chosen maturity
    -- required for a rectangular grid. Optionally restrict to a moneyness band
    around spot to keep the request small and relevant, and to favor strikes
    that are more likely to actually have traded recently.
    """
    all_expirations = sorted(strikes_by_expiry.keys())
    print(f"All available expirations ({len(all_expirations)}): {all_expirations}")

    expirations = all_expirations[:n_expirations]

    if not expirations:
        raise ValueError(
            f"No expirations found at least {min_days_out} days out. "
            "Check that the symbol has active option contracts."
        )

    common = set.intersection(*(strikes_by_expiry[e] for e in expirations))
    if spot is not None:
        lo, hi = moneyness_band
        common = {k for k in common if lo * spot <= k <= hi * spot}

    return expirations, sorted(common)


def fetch_quotes(symbols: list[str]) -> dict:
    """Latest quote (mid of bid/ask) for a batch of option symbols.
    Alpaca caps a single request at 100 symbols, so we chunk and merge."""
    if not symbols:
        return {}

    mids = {}
    chunk_size = 100
    for i in range(0, len(symbols), chunk_size):
        chunk = symbols[i:i + chunk_size]
        req = OptionLatestQuoteRequest(symbol_or_symbols=chunk)
        quotes = option_data_client.get_option_latest_quote(req)
        for sym, q in quotes.items():
            bid, ask = q.bid_price, q.ask_price
            if bid and ask:
                mids[sym] = (bid + ask) / 2.0
            elif bid or ask:
                mids[sym] = bid or ask

    return mids


def fetch_recent_closes(symbols: list[str], lookback_days=14) -> dict:
    """
    Last available daily close over the past lookback_days, for symbols that have
    no live quote and no close_price on the contract itself. Illiquid strikes often
    haven't traded on the single day a close_price snapshot would reflect, so this
    looks back further to find the last time they actually traded.
    """
    if not symbols:
        return {}

    closes = {}
    chunk_size = 100
    end = datetime.now()
    start = end - timedelta(days=lookback_days)

    for i in range(0, len(symbols), chunk_size):
        chunk = symbols[i:i + chunk_size]
        req = OptionBarsRequest(symbol_or_symbols=chunk, timeframe=TimeFrame.Day, start=start, end=end)
        bars = option_data_client.get_option_bars(req).data
        for sym in chunk:
            if sym in bars and len(bars[sym]) > 0:
                closes[sym] = float(bars[sym][-1].close)

    return closes


def _try_build_grid(symbol, spot, strikes_by_expiry, lookup, n_expirations, min_days_out, moneyness_band):
    """One attempt at building the grid for a given (n_expirations, moneyness_band)."""
    expirations, strikes = pick_expirations_and_strikes(
        strikes_by_expiry, min_days_out=min_days_out,
        n_expirations=n_expirations, moneyness_band=moneyness_band, spot=spot,
    )

    if len(strikes) < 3:
        return None  # not enough candidate strikes even before fetching prices

    today = date.today()
    maturities = np.array(sorted((e - today).days / 365 for e in expirations))
    expiry_by_T = {(e - today).days / 365: e for e in expirations}

    all_symbols = [lookup[(e, k)][0] for e in expirations for k in strikes]
    live_mids = fetch_quotes(all_symbols)

    market_prices = pd.DataFrame(index=strikes, columns=maturities, dtype=float)
    symbol_for_cell = {}
    used_fallback = False
    for T in maturities:
        e = expiry_by_T[T]
        for k in strikes:
            sym, close_price = lookup[(e, k)]
            symbol_for_cell[(k, T)] = sym
            price = live_mids.get(sym)
            if price is None:
                price = close_price
                used_fallback = True
            market_prices.loc[k, T] = price

    still_missing = market_prices.isna()
    if still_missing.any().any():
        missing_symbols = [symbol_for_cell[(k, T)] for T in maturities for k in strikes
                            if still_missing.loc[k, T]]
        recent_closes = fetch_recent_closes(missing_symbols)
        for T in maturities:
            for k in strikes:
                if still_missing.loc[k, T]:
                    sym = symbol_for_cell[(k, T)]
                    if sym in recent_closes:
                        market_prices.loc[k, T] = recent_closes[sym]
                        used_fallback = True

    incomplete_strikes = market_prices.index[market_prices.isna().any(axis=1)]
    if len(incomplete_strikes) > 0:
        market_prices = market_prices.drop(index=incomplete_strikes)
        strikes = market_prices.index.to_numpy(dtype=float)

    if market_prices.empty or len(strikes) < 3:
        return None

    if used_fallback:
        print("Note: some contracts had no live quote (market closed?) and used close_price or a recent bar instead.")

    return spot, np.array(strikes, dtype=float), maturities, market_prices


def build_market_price_grid(symbol: str, n_expirations=6, min_days_out=3,
                             moneyness_band=(0.80, 1.20)):
    """
    Returns (S0, strikes, maturities, market_prices) where market_prices is a
    DataFrame indexed by strike, columned by maturity (years) -- a full
    rectangular grid of real call prices.

    Price for each cell is resolved in this order:
    1. Live quote (mid of bid/ask)
    2. The contract's own close_price field
    3. Last daily close over the past two weeks (for illiquid strikes with no
       close_price recorded at all)

    Liquidity for far-from-the-money strikes varies day to day, so instead of
    failing when the requested band doesn't have enough usable data, this
    automatically retries with a narrower band first (most likely to have
    real recent activity), then widens if that still isn't enough.
    """
    spot = get_spot_price(symbol)
    strikes_by_expiry, lookup = get_call_contracts(symbol, min_days_out=min_days_out)

    lo, hi = moneyness_band
    attempts = [
        (min(n_expirations, 3), (0.97, 1.03)),   # tightest: near-the-money, few maturities
        (min(n_expirations, 4), (0.93, 1.07)),
        (n_expirations, (0.85, 1.15)),
        (n_expirations, moneyness_band),         # whatever the caller originally asked for
    ]

    for attempt_n_exp, attempt_band in attempts:
        print(f"Trying n_expirations={attempt_n_exp}, moneyness_band={attempt_band}...")
        result = _try_build_grid(symbol, spot, strikes_by_expiry, lookup,
                                  attempt_n_exp, min_days_out, attempt_band)
        if result is not None:
            _, strikes, _, _ = result
            print(f"Succeeded with {len(strikes)} strikes.")
            return result

    raise ValueError(
        f"Could not find enough strikes with usable price data for {symbol} "
        "across several attempted configurations. The market may be very quiet "
        "right now -- try again during regular trading hours."
    )
