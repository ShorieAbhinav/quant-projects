import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

ticker = "AAPL"
data = yf.download(ticker, start="2020-01-01", end ="2026-03-01")

def calculate_ema(prices, N):
    k = 2 / (N + 1)
    ema = [prices[0]]

    for i in range(1, len(prices)):
        today_ema = (prices[i] * k) + (ema[i-1]*(1-k))
        ema.append(today_ema)

    return ema

prices = data["Close"]["AAPL"].tolist()

if len(prices) == 0:
    print("No data downloaded - check your date range")
else:
    ema_8 = calculate_ema(prices, 8)
    ema_33 = calculate_ema(prices, 33)

    signals = []

    for i in range(len(ema_8)):
        if ema_8[i] > ema_33[i]:
            signals.append(1) # Buy signal
        else:
            signals.append(0) # Hold signal


    results = pd.DataFrame({
        "Close": prices,
        "EMA_8": ema_8,
        "EMA_33": ema_33,
        "Signal": signals
    })

    results["Daily_Return"] = results["Close"].pct_change()

    # shift signal by 1 — we trade next day's open, not today's close
    # this prevents lookahead bias
    results["Strategy_Return"] = results["Daily_Return"] * results["Signal"].shift(1)

    results["Cumulative_Market"] = (1 + results["Daily_Return"]).cumprod()
    results["Cumulative_Strategy"] = (1 + results["Strategy_Return"]).cumprod()

    total_return = results["Cumulative_Strategy"].iloc[-1] - 1
    market_return = results["Cumulative_Market"].iloc[-1] - 1

    sharpe = (results["Strategy_Return"].mean() / results["Strategy_Return"].std() * (252**0.5))

    max_drawdown = (results["Cumulative_Strategy"] / results["Cumulative_Strategy"].cummax() - 1).min()

    print(f"Strategy Total Return: {total_return:.2%}")
    print(f"Market Total Return: {market_return:.2%}")
    print(f"Strategy Sharpe Ratio: {sharpe:.2f}")
    print(f"Strategy Max Drawdown: {max_drawdown:.2%}")

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))

    # Plot 1 - Price and EMAs
    ax1.plot(prices, label="AAPL Price", alpha=0.7, color="white")
    ax1.plot(ema_8, label="EMA 8 (Fast)", alpha=0.9, color="cyan")
    ax1.plot(ema_33, label="EMA 33 (Slow)", alpha=0.9, color="orange")
    ax1.set_title("AAPL Price with 8/33 EMA Crossover")
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # Plot 2 - Cumulative returns
    ax2.plot(results["Cumulative_Market"].values, 
            label="Buy & Hold", color="orange")
    ax2.plot(results["Cumulative_Strategy"].values, 
            label="EMA Strategy", color="cyan")
    ax2.set_title("Strategy vs Buy & Hold")
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig("ema_crossover_results.png")
    plt.show()

    print("Chart saved!")