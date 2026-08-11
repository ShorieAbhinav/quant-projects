import numpy as np
import plotly.graph_objects as go

DARK_BG = "#0b0d0f"
GRID_COLOR = "#333333"


def plot_3d_surface(symbol, S0, strikes, maturities, implied_surface, spline, n_grid=300):
    """Smooth 3D implied vol surface, with the actual solved grid points overlaid as markers."""
    # strike: descending
    strike_grid = np.linspace(float(strikes.max()), float(strikes.min()), n_grid)
    # time: ascending
    t_grid = np.linspace(float(maturities.min()), float(maturities.max()), n_grid)

    K_grid, T_grid = np.meshgrid(strike_grid, t_grid)
    M_grid = K_grid / S0

    Z_vol = spline.ev(M_grid.ravel(), T_grid.ravel()).reshape(K_grid.shape)
    Z_vol = np.clip(Z_vol, 0.01, 3.0)

    surface = go.Surface(
        x=T_grid,               # Time (years)
        y=K_grid,               # Strike
        z=Z_vol * 100.0,        # Vol (%)
        colorscale="Plasma",
        opacity=0.93,
        contours={
            "z": {"show": True, "usecolormap": True, "highlightcolor": "white", "project_z": True}
        },
        lighting=dict(ambient=0.6, diffuse=0.8, specular=0.3, roughness=0.5),
        lightposition=dict(x=100, y=200, z=150),
        colorbar=dict(title="Implied vol (%)", len=0.75, tickfont=dict(color="white"),
                       title_font=dict(color="white")),
        name="Spline surface",
    )

    dots_x, dots_y, dots_z = [], [], []
    for T in np.sort(maturities):
        for K in strikes:
            dots_x.append(float(T))
            dots_y.append(float(K))
            dots_z.append(float(implied_surface.loc[K, T]) * 100.0)

    dots = go.Scatter3d(
        x=dots_x, y=dots_y, z=dots_z,
        mode="markers",
        marker=dict(size=3, color="white", opacity=0.6),
        name="IV grid points",
    )

    fig = go.Figure(data=[surface, dots])
    fig.update_layout(
        title=dict(
            text=f"{symbol} — Implied Volatility Surface (x=Time, y=Strike, z=Vol)",
            x=0.5, xanchor="center",
            pad=dict(t=2, b=2),
            font=dict(color="white"),
        ),
        height=820,
        width=1120,
        margin=dict(l=0, r=0, t=35, b=0),
        paper_bgcolor=DARK_BG,
        font=dict(color="white"),
        scene=dict(
            domain=dict(x=[0.0, 1.0], y=[0.0, 1.0]),
            xaxis=dict(title="Time to maturity (years)", autorange="reversed",
                       backgroundcolor=DARK_BG, gridcolor=GRID_COLOR, color="white"),
            yaxis=dict(title="Strike (K)",
                       backgroundcolor=DARK_BG, gridcolor=GRID_COLOR, color="white"),
            zaxis=dict(title="Implied volatility (percent)",
                       backgroundcolor=DARK_BG, gridcolor=GRID_COLOR, color="white"),
            camera=dict(eye=dict(x=1.35, y=1.35, z=0.9)),
        ),
    )
    return fig


def plot_smile(symbol, S0, implied_surface):
    """Implied volatility versus strike, one line per maturity."""
    fig = go.Figure()
    for t in implied_surface.columns:
        fig.add_trace(
            go.Scatter(
                x=implied_surface.index.to_numpy(dtype=float),
                y=(implied_surface[t].to_numpy(dtype=float) * 100.0),
                mode="lines+markers",
                name=f"Time to maturity = {float(t):.4f} years",
            )
        )
    fig.add_vline(x=S0, line_dash="dash", line_color="white")
    fig.update_layout(
        title=f"{symbol} — Volatility Smile (Implied volatility versus strike)",
        xaxis_title="Strike",
        yaxis_title="Implied volatility (percent)",
        height=480,
        paper_bgcolor=DARK_BG,
        plot_bgcolor=DARK_BG,
        font=dict(color="white"),
        xaxis=dict(gridcolor=GRID_COLOR),
        yaxis=dict(gridcolor=GRID_COLOR),
    )
    return fig


def plot_term_structure(symbol, S0, implied_surface):
    """Implied volatility versus maturity, for a few strikes nearest the money."""
    strike_array = implied_surface.index.to_numpy(dtype=float)
    atm_index = int(np.argmin(np.abs(strike_array - S0)))
    selected_strikes = strike_array[max(0, atm_index - 2): min(len(strike_array), atm_index + 3)]

    fig = go.Figure()
    for k in selected_strikes:
        fig.add_trace(
            go.Scatter(
                x=implied_surface.columns.to_numpy(dtype=float),
                y=(implied_surface.loc[k].to_numpy(dtype=float) * 100.0),
                mode="lines+markers",
                name=f"Strike = {k:.0f}",
            )
        )
    fig.update_layout(
        title=f"{symbol} — Volatility Term Structure (Implied volatility versus maturity)",
        xaxis_title="Time to maturity (years)",
        yaxis_title="Implied volatility (percent)",
        height=480,
        paper_bgcolor=DARK_BG,
        plot_bgcolor=DARK_BG,
        font=dict(color="white"),
        xaxis=dict(gridcolor=GRID_COLOR),
        yaxis=dict(gridcolor=GRID_COLOR),
    )
    return fig
