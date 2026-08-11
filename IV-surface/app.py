"""
Implied Volatility Dashboard (Dash version)

Pick a stock, see its live implied volatility surface, smile, and term
structure, plus the underlying price grid -- all in one page. Auto-refreshes
on an interval (pausable), reusing the same alpaca_data / vol_surface /
plots modules as main.py and live_surface.py.
"""

import traceback

import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State

from alpaca_data import build_market_price_grid
from vol_surface import build_implied_vol_grid, fit_spline, reprice_and_check
from plots import plot_3d_surface, plot_smile, plot_term_structure

SYMBOLS = ["AAPL", "NVDA", "TSLA", "QQQ", "SPY", "MSFT", "META", "GOOGL", "AMD"]
r = 0.05    # approximate risk-free rate
q = 0.005   # approximate dividend yield

DARK_BG = "#0b0d0f"
PANEL_BG = "#161b22"
TEXT_COLOR = "#e6e6e6"

REFRESH_OPTIONS = [
    {"label": "Manual only", "value": "manual"},
    {"label": "Every 5s", "value": "5"},
    {"label": "Every 15s", "value": "15"},
    {"label": "Every 30s", "value": "30"},
    {"label": "Every 60s", "value": "60"},
]

app = dash.Dash(__name__)
app.title = "Implied Volatility Dashboard"

app.layout = html.Div(
    style={"backgroundColor": DARK_BG, "color": TEXT_COLOR, "minHeight": "100vh",
           "fontFamily": "Helvetica, Arial, sans-serif", "padding": "24px"},
    children=[
        html.H1("Implied Volatility Dashboard", style={"marginBottom": "4px"}),
        html.P("Real options data from Alpaca, priced with a hand-built Black-Scholes model "
               "and a bisection implied volatility solver.",
               style={"color": "#999", "marginTop": 0, "marginBottom": "20px"}),

        # Controls
        html.Div(
            style={"display": "flex", "gap": "16px", "alignItems": "center",
                   "flexWrap": "wrap", "marginBottom": "16px"},
            children=[
                html.Div([
                    html.Label("Symbol", style={"display": "block", "fontSize": "12px", "color": "#999"}),
                    dcc.Dropdown(
                        id="symbol-dropdown",
                        options=[{"label": s, "value": s} for s in SYMBOLS],
                        value=SYMBOLS[0],
                        clearable=False,
                        style={"width": "160px", "color": "#000"},
                    ),
                ]),
                html.Div([
                    html.Label("Auto-refresh", style={"display": "block", "fontSize": "12px", "color": "#999"}),
                    dcc.Dropdown(
                        id="refresh-dropdown",
                        options=REFRESH_OPTIONS,
                        value="manual",
                        clearable=False,
                        style={"width": "160px", "color": "#000"},
                    ),
                ]),
                html.Button("Refresh now", id="refresh-button", n_clicks=0,
                            style={"height": "38px", "marginTop": "18px", "padding": "0 16px",
                                   "backgroundColor": "#1f2329", "color": "white", "border": "1px solid #444",
                                   "borderRadius": "4px", "cursor": "pointer"}),
                html.Div(id="status-text",
                          style={"marginTop": "18px", "fontSize": "13px", "color": "#999"}),
            ],
        ),

        dcc.Interval(id="interval-component", interval=5000, disabled=True, n_intervals=0),

        dcc.Loading(
            type="circle",
            color="#00f2ff",
            children=[
                dcc.Graph(id="surface-graph", style={"height": "700px"}),
                html.Div(
                    style={"display": "flex", "gap": "16px", "flexWrap": "wrap"},
                    children=[
                        dcc.Graph(id="smile-graph", style={"flex": "1", "minWidth": "420px"}),
                        dcc.Graph(id="term-graph", style={"flex": "1", "minWidth": "420px"}),
                    ],
                ),
                html.H3("Market call prices C(K, T)", style={"marginTop": "24px"}),
                dash_table.DataTable(
                    id="price-table",
                    style_table={"overflowX": "auto"},
                    style_header={"backgroundColor": PANEL_BG, "color": "white", "fontWeight": "bold"},
                    style_cell={"backgroundColor": DARK_BG, "color": TEXT_COLOR,
                                "border": "1px solid #333", "padding": "6px", "textAlign": "center"},
                ),
            ],
        ),
    ],
)


@app.callback(
    Output("interval-component", "interval"),
    Output("interval-component", "disabled"),
    Input("refresh-dropdown", "value"),
)
def update_interval(refresh_value):
    if refresh_value == "manual":
        return 5000, True
    return int(refresh_value) * 1000, False


@app.callback(
    Output("surface-graph", "figure"),
    Output("smile-graph", "figure"),
    Output("term-graph", "figure"),
    Output("price-table", "data"),
    Output("price-table", "columns"),
    Output("status-text", "children"),
    Input("refresh-button", "n_clicks"),
    Input("interval-component", "n_intervals"),
    Input("symbol-dropdown", "value"),
    prevent_initial_call=False,
)
def refresh_all(_n_clicks, _n_intervals, symbol):
    try:
        S0, strikes, maturities, market_prices = build_market_price_grid(
            symbol, n_expirations=6, min_days_out=3, moneyness_band=(0.80, 1.20)
        )

        implied_surface = build_implied_vol_grid(S0, strikes, maturities, market_prices, r, q=q)
        spline = fit_spline(S0, strikes, maturities, implied_surface, smoothing=0.0)
        abs_price_err = reprice_and_check(S0, strikes, maturities, implied_surface, market_prices, r, q=q)
        max_err = float(abs_price_err.max().max())

        fig_surface = plot_3d_surface(symbol, S0, strikes, maturities, implied_surface, spline)
        fig_smile = plot_smile(symbol, S0, implied_surface)
        fig_term = plot_term_structure(symbol, S0, implied_surface)

        table_df = market_prices.round(2).reset_index().rename(columns={"index": "Strike"})
        table_df.columns = ["Strike"] + [f"T={float(c):.3f}y" for c in market_prices.columns]
        table_data = table_df.to_dict("records")
        table_columns = [{"name": c, "id": c} for c in table_df.columns]

        status = (f"{symbol} spot: {S0:.2f} | {len(strikes)} strikes x {len(maturities)} maturities | "
                  f"max repricing error: {max_err:.2e}")

        return fig_surface, fig_smile, fig_term, table_data, table_columns, status

    except Exception as e:
        empty_fig = {
            "data": [],
            "layout": {"paper_bgcolor": DARK_BG, "plot_bgcolor": DARK_BG,
                       "font": {"color": TEXT_COLOR},
                       "title": "No data -- see error below"},
        }
        error_msg = f"Error loading {symbol}: {e}"
        print(traceback.format_exc())
        return empty_fig, empty_fig, empty_fig, [], [], error_msg


if __name__ == "__main__":
    app.run(debug=True, port=8050)
