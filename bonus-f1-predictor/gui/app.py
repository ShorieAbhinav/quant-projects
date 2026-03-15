import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import sys
import os

# add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from data.fetch_qualifying import get_qualifying_results
from data.fetch_historical import get_chaos_coefficient
from model.scorer import score_drivers
from model.monte_carlo import run_simulation

# ── Page config ───────────────────────────────────────────────
st.set_page_config(
    page_title="F1 Race Predictor",
    page_icon="🏎️",
    layout="wide"
)

# ── Author tag ─────────────────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.markdown("**Built by:** Abhinav Shorie")
st.sidebar.markdown("**Stack:** FastF1 · Python · Monte Carlo")
st.sidebar.markdown("**GitHub:** [ShorieAbhinav](https://github.com/ShorieAbhinav)")

# -- Header ----------------------------------------------------
st.title("🏎️ F1 Race Predictor")
st.subheader("2026 Chinese Grand Prix — Monte Carlo Simulation")
st.markdown("---")

# ── Load data with caching ─────────────────────────────────────
@st.cache_data
def load_predictions():
    """
    Cached data loader — only runs once per session.
    Streamlit reruns the whole script on every interaction
    so caching prevents re-fetching data every time.
    """
    drivers = get_qualifying_results()
    scored = score_drivers(drivers)
    chaos = get_chaos_coefficient()
    results = run_simulation(scored, chaos)
    return results, chaos

# show spinner while loading
with st.spinner("Running 100,000 race simulations..."):
    results, chaos = load_predictions()

# ── Top metrics ────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="🏆 Predicted Winner",
        value=results[0]["name"],
        delta=f"{results[0]['mc_win_probability']*100:.1f}% win chance"
    )

with col2:
    st.metric(
        label="🥈 Predicted P2",
        value=results[1]["name"],
        delta=f"{results[1]['mc_win_probability']*100:.1f}% win chance"
    )

with col3:
    st.metric(
        label="🥉 Predicted P3",
        value=results[2]["name"],
        delta=f"{results[2]['mc_win_probability']*100:.1f}% win chance"
    )

with col4:
    st.metric(
        label="🌀 Chaos Coefficient",
        value=f"{chaos:.2f}",
        delta="avg position changes at Shanghai"
    )

st.markdown("---")

# ── Win probability bar chart ──────────────────────────────────
st.subheader("🏁 Win Probability by Driver")

# team colors for the chart
team_colors = {
    "Mercedes":         "#00D2BE",
    "Ferrari":          "#DC0000",
    "McLaren":          "#FF8000",
    "Red Bull Racing":  "#3671C6",
    "Alpine":           "#FF87BC",
    "Haas F1 Team":     "#B6BABD",
    "Racing Bulls":     "#6692FF",
    "Audi":             "#E8002D",
    "Williams":         "#64C4FF",
    "Aston Martin":     "#358C75",
    "Cadillac":         "#FFFFFF",
}

colors = [team_colors.get(d["team"], "#888888") for d in results]

fig_win = go.Figure(go.Bar(
    x=[d["name"] for d in results],
    y=[d["mc_win_probability"] * 100 for d in results],
    marker_color=colors,
    text=[f"{d['mc_win_probability']*100:.1f}%" for d in results],
    textposition="outside",
    hovertemplate="<b>%{x}</b><br>Win: %{y:.2f}%<extra></extra>"
))

fig_win.update_layout(
    plot_bgcolor="#0D1117",
    paper_bgcolor="#0D1117",
    font_color="#E6EDF3",
    xaxis=dict(tickangle=-45, gridcolor="#21262D"),
    yaxis=dict(
        title="Win Probability (%)",
        gridcolor="#21262D"
    ),
    height=450,
    showlegend=False,
    margin=dict(t=20, b=120)
)

st.plotly_chart(fig_win, use_container_width=True)
st.markdown("---")

# ── Podium probability chart ───────────────────────────────────
st.subheader("🏅 Podium Probability by Driver")

fig_podium = go.Figure(go.Bar(
    x=[d["name"] for d in results],
    y=[d["mc_podium_probability"] * 100 for d in results],
    marker_color=colors,
    text=[f"{d['mc_podium_probability']*100:.1f}%" for d in results],
    textposition="outside",
    hovertemplate="<b>%{x}</b><br>Podium: %{y:.2f}%<extra></extra>"
))

fig_podium.update_layout(
    plot_bgcolor="#0D1117",
    paper_bgcolor="#0D1117",
    font_color="#E6EDF3",
    xaxis=dict(tickangle=-45, gridcolor="#21262D"),
    yaxis=dict(
        title="Podium Probability (%)",
        gridcolor="#21262D"
    ),
    height=450,
    showlegend=False,
    margin=dict(t=20, b=120)
)

st.plotly_chart(fig_podium, use_container_width=True)
st.markdown("---")

# ── Full predictions table ─────────────────────────────────────
st.subheader("📊 Full Predictions Table")

table_data = []
for i, driver in enumerate(results):
    table_data.append({
        "Rank":     i + 1,
        "Driver":   driver["name"],
        "Team":     driver["team"],
        "Grid":     f"P{driver['grid_position']}",
        "Win %":    f"{driver['mc_win_probability']*100:.2f}%",
        "Podium %": f"{driver['mc_podium_probability']*100:.2f}%",
    })

st.dataframe(
    table_data,
    use_container_width=True,
    hide_index=True,
)

st.markdown("---")

# ── Model info ─────────────────────────────────────────────────
st.subheader("ℹ️ Model Information")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    **Scoring Weights:**
    - Grid Position: 35%
    - Qualifying Pace: 25%
    - Sprint Result: 15%
    - Constructor Pace: 15%
    - Shanghai History: 10%
    """)

with col2:
    st.markdown(f"""
    **Simulation Parameters:**
    - Simulations: 100,000
    - Chaos Coefficient: {chaos:.2f}
    - Safety Car Probability: 35%
    - Data Source: FastF1 API
    """)

st.markdown("---")
st.caption("Built by Abhinav Shorie · FastF1 + Monte Carlo Simulation · 2026")