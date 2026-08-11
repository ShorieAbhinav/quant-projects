"""
Live Implied Volatility Surface (Alpaca version)

Adapted from Quant Guild's IBKR-based live surface script. Since Alpaca's
REST API doesn't push continuous ticks the way IBKR's TWS socket does, this
polls the option chain on a fixed interval in a background thread instead,
and redraws on the main thread -- same lock/unlock button pattern, same
dark 3D-surface-plus-skew layout.
"""

import threading
import time

import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.widgets import Button

from alpaca_data import build_market_price_grid
from vol_surface import build_implied_vol_grid, fit_spline

plt.style.use('dark_background')

SYMBOLS = ["AAPL", "NVDA", "TSLA", "QQQ", "SPY", "MSFT", "META", "GOOGL", "AMD"]
r = 0.05
q = 0.005
REFRESH_SECONDS = 5  # how often to re-poll Alpaca; keep this modest to respect rate limits


def choose_symbol():
    print("Choose a symbol:")
    for i, sym in enumerate(SYMBOLS, start=1):
        print(f"  {i}. {sym}")
    choice = input(f"Enter a number (1-{len(SYMBOLS)}): ").strip()
    try:
        return SYMBOLS[int(choice) - 1]
    except (ValueError, IndexError):
        print(f"Invalid choice, defaulting to {SYMBOLS[0]}.")
        return SYMBOLS[0]


class LiveSurfaceState:
    """Shared state between the polling thread and the plotting thread."""

    def __init__(self):
        self.lock = threading.Lock()
        self.spot = None
        self.implied_surface = None  # DataFrame: index=strikes, columns=maturities(years)
        self.last_update = None
        self.error = None
        self.stop_event = threading.Event()

    def set_data(self, spot, implied_surface):
        with self.lock:
            self.spot = spot
            self.implied_surface = implied_surface
            self.last_update = time.strftime('%H:%M:%S')
            self.error = None

    def set_error(self, message):
        with self.lock:
            self.error = message

    def get_snapshot(self):
        with self.lock:
            return self.spot, self.implied_surface, self.last_update, self.error


def poll_loop(state: LiveSurfaceState, symbol: str):
    """Background thread: refresh the implied vol grid every REFRESH_SECONDS."""
    while not state.stop_event.is_set():
        try:
            S0, strikes, maturities, market_prices = build_market_price_grid(
                symbol, n_expirations=6, min_days_out=1, moneyness_band=(0.85, 1.15)
            )
            implied_surface = build_implied_vol_grid(S0, strikes, maturities, market_prices, r, q=q)
            state.set_data(S0, implied_surface)
            print(f"[{time.strftime('%H:%M:%S')}] Refreshed grid: "
                  f"{len(strikes)} strikes x {len(maturities)} maturities, spot={S0:.2f}")
        except Exception as e:
            state.set_error(str(e))
            print(f"[{time.strftime('%H:%M:%S')}] Refresh failed: {e}")

        state.stop_event.wait(REFRESH_SECONDS)


class PlotState:
    def __init__(self):
        self.is_locked = False

    def toggle(self, event):
        self.is_locked = not self.is_locked
        btn_label.set_text("UNLOCK UPDATES" if self.is_locked else "LOCK UPDATES")
        plt.draw()


def live_desktop_plot(state: LiveSurfaceState, symbol: str):
    plt.ion()
    fig = plt.figure(figsize=(16, 9))
    fig.canvas.manager.set_window_title(f"Live Implied Volatility Surface - {symbol}")
    fig.patch.set_facecolor('#0b0d0f')

    ax_3d = plt.subplot2grid((1, 3), (0, 0), colspan=2, projection='3d')
    ax_skew = plt.subplot2grid((1, 3), (0, 2))

    plot_state = PlotState()
    ax_button = plt.axes([0.42, 0.03, 0.12, 0.04])
    global btn_label
    btn = Button(ax_button, 'LOCK UPDATES', color='#1f2329', hovercolor='#2d333b')
    btn_label = btn.label
    btn_label.set_color('white')
    btn_label.set_fontsize(9)
    btn.on_clicked(plot_state.toggle)

    print(f"--- Live {symbol} Volatility Surface Started (refresh every {REFRESH_SECONDS}s) ---")

    try:
        while True:
            if not plot_state.is_locked:
                spot, implied_surface, last_update, error = state.get_snapshot()

                if error is not None:
                    ax_3d.clear()
                    ax_3d.set_facecolor('#0b0d0f')
                    ax_3d.set_title(f"Waiting for data... ({error})", color='#ff5555', fontsize=10)

                elif implied_surface is not None:
                    # implied_surface: index=strikes, columns=maturities (years)
                    strikes = implied_surface.index.to_numpy(dtype=float)
                    maturities = implied_surface.columns.to_numpy(dtype=float)

                    curr_elev, curr_azim = ax_3d.elev, ax_3d.azim
                    ax_3d.clear()
                    ax_3d.set_facecolor('#0b0d0f')

                    try:
                        spline = fit_spline(spot, strikes, maturities, implied_surface, smoothing=0.0)

                        n_grid = 60
                        strike_grid = np.linspace(strikes.min(), strikes.max(), n_grid)
                        t_grid = np.linspace(maturities.min(), maturities.max(), n_grid)
                        K_grid, T_grid = np.meshgrid(strike_grid, t_grid)
                        M_grid = K_grid / spot

                        Z_smooth = spline.ev(M_grid.ravel(), T_grid.ravel()).reshape(K_grid.shape)
                        Z_smooth = np.clip(Z_smooth, 0.01, 3.0) * 100.0  # percent

                        # T_grid mapped to the same y-axis index scale as the maturity ticks below
                        T_idx_grid = np.interp(T_grid, maturities, np.arange(len(maturities)))

                        ax_3d.plot_surface(K_grid, T_idx_grid, Z_smooth, cmap='magma',
                                            edgecolor='none', alpha=0.92, antialiased=True)

                        # Overlay the actual solved grid points for reference
                        for j, T in enumerate(maturities):
                            z_vals = implied_surface[T].to_numpy(dtype=float) * 100.0
                            ax_3d.scatter(strikes, [j] * len(strikes), z_vals,
                                          color='white', s=14, alpha=0.8, depthshade=False)

                    except Exception as spline_err:
                        # Fall back to the raw flat-shaded grid if the spline can't be fit
                        # (e.g. too few strikes/maturities right after a fresh poll)
                        Z = implied_surface.to_numpy(dtype=float).T * 100.0
                        X, Y_idx = np.meshgrid(strikes, np.arange(len(maturities)))
                        ax_3d.plot_surface(X, Y_idx, Z, cmap='magma', edgecolor='white', lw=0.1, alpha=0.9)
                        print(f"Spline fit failed, showing raw grid instead: {spline_err}")

                    ax_3d.set_yticks(np.arange(len(maturities)))
                    ax_3d.set_yticklabels([f"{t:.3f}y" for t in maturities], fontsize=8)
                    ax_3d.set_xlabel("Strike", color='white')
                    ax_3d.set_ylabel("Time to maturity (years)", color='white')
                    ax_3d.set_zlabel("Implied Vol (%)", color='white')
                    ax_3d.set_title(f"LIVE IV SURFACE | {symbol} | {last_update}", color='white')
                    ax_3d.view_init(elev=curr_elev, azim=curr_azim)

                    # Skew for nearest maturity
                    ax_skew.clear()
                    ax_skew.set_facecolor('#161b22')
                    nearest_T = maturities[0]
                    skew_vals = implied_surface[nearest_T].to_numpy(dtype=float) * 100.0

                    ax_skew.plot(strikes, skew_vals, marker='o', color='#00f2ff')
                    if spot is not None:
                        ax_skew.axvline(x=spot, color='#ff3e3e', linestyle='--')
                    ax_skew.set_title(f"FRONT-MONTH SKEW: T={nearest_T:.3f}y", color='white')
                    ax_skew.set_xlabel("Strike", color='white')
                    ax_skew.set_ylabel("Implied Vol (%)", color='white')

            plt.pause(0.5)

    except KeyboardInterrupt:
        state.stop_event.set()
        plt.close()


if __name__ == "__main__":
    symbol = choose_symbol()
    shared_state = LiveSurfaceState()

    poll_thread = threading.Thread(target=poll_loop, args=(shared_state, symbol), daemon=True)
    poll_thread.start()

    print("Waiting for first data pull...")
    time.sleep(3)  # brief buffer before first plot draw

    live_desktop_plot(shared_state, symbol)
