# 🏎️ F1 Race Predictor — Monte Carlo Simulation

A race winner prediction system for Formula 1 that combines 
a weighted scoring model with Monte Carlo simulation to produce 
win and podium probabilities for every driver on the grid.

## How It Works

### Stage 1 — Data Pipeline
- Pulls 18 years of Chinese GP historical data via FastF1
- Calculates a **chaos coefficient** (3.60) representing average 
  position change at Shanghai across all historical races
- Automatically fetches live qualifying and sprint results 
  for the current race weekend

### Stage 2 — Weighted Scoring Model
Converts each driver's data into a base score using 5 factors:

| Factor | Weight | Why |
|---|---|---|
| Grid Position | 35% | Strongest single predictor in F1 |
| Qualifying Pace | 25% | Direct measure of car + driver pace |
| Sprint Result | 15% | Recent form on same circuit |
| Constructor Pace | 15% | Underlying car performance |
| Shanghai History | 10% | Track knowledge and circuit affinity |

Uses **exponential decay** for grid position and qualifying gap 
so front-row advantage is correctly weighted over back-of-grid.

### Stage 3 — Monte Carlo Simulation
Runs 100,000 simulated races on top of base probabilities:
- Random position noise scaled by chaos coefficient
- Per-team DNF probability applied each simulation
- 35% safety car probability compressing the field
- Weighted random finishing order drawn each simulation

### Stage 4 — API + Dashboard
- **FastAPI** REST endpoints serving predictions as JSON
- **Streamlit** interactive dashboard with team-color charts

## 2026 Chinese GP Predictions

| Rank | Driver | Team | Win % | Podium % |
|---|---|---|---|---|
| 1 | Kimi Antonelli | Mercedes | 10.3% | 29.2% |
| 2 | George Russell | Mercedes | 9.8% | 28.3% |
| 3 | Lewis Hamilton | Ferrari | 8.8% | 25.7% |
| 4 | Charles Leclerc | Ferrari | 8.0% | 23.7% |
| 5 | Oscar Piastri | McLaren | 7.1% | 21.1% |

*Predictions generated pre-race on March 14, 2026*

## Project Structure


## Stack
- **FastF1** — live F1 timing and results data
- **NumPy** — Monte Carlo simulation engine
- **FastAPI** — REST API serving predictions
- **Streamlit** — interactive prediction dashboard
- **Plotly** — interactive charts with official team colors

## API Endpoints

| Endpoint | Description |
|---|---|
| `GET /` | Available endpoints |
| `GET /chaos-coefficient` | Shanghai chaos coefficient |
| `GET /drivers` | Scored and ranked grid |
| `GET /simulate` | Full Monte Carlo predictions |

## Running Locally

```bash
# Install dependencies
pip install fastf1 fastapi uvicorn streamlit plotly numpy pandas

# Run dashboard
streamlit run gui/app.py

# Run API
uvicorn api.main:app --reload
