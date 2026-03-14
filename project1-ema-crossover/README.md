# Project 1 — EMA 8/33 Crossover Strategy

## What this is
A systematic long-only trading strategy using 8 and 33 period 
Exponential Moving Average crossovers to generate buy and flat 
signals on AAPL stock.

## Strategy Logic
- BUY when 8 EMA crosses above 33 EMA (uptrend confirmed)
- HOLD CASH when 8 EMA crosses below 33 EMA (downtrend)
- No short selling — long only

## Concepts covered
- Exponential Moving Average (EMA) built from scratch using recursive formula
- Signal generation from EMA crossovers
- Lookahead bias prevention using signal shifting
- Backtesting against 6 years of real market data
- Performance metrics: Sharpe ratio, max drawdown, total return

## Results (AAPL, Jan 2020 — Mar 2026)
| Metric | Strategy | Buy & Hold |
|---|---|---|
| Total Return | 79.68% | 264.89% |
| Sharpe Ratio | 0.57 | — |
| Max Drawdown | -27.98% | ~-35% |

## Key Findings
- Strategy underperformed buy and hold on a strong bull run stock
- However max drawdown was significantly lower (28% vs 35%)
- Short selling was tested and removed — going short Apple during 
  a 6 year bull run destroyed returns (-39% total return)
- Strategy would perform better on mean-reverting or sideways assets

## Next Steps
- Add RSI filter to avoid overbought entries (Project 2)
- Test on multiple assets not just Apple
- Implement multi-timeframe analysis (daily trend + hourly entry)
- Add position sizing based on volatility

## Libraries
- pandas, numpy, yfinance, matplotlib

## How to run
```bash
python ema_crossover.py
```