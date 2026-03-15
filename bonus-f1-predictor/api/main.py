from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sys
import os

# add parent directory to path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from data.fetch_qualifying import get_qualifying_results
from data.fetch_historical import get_chaos_coefficient
from model.scorer import score_drivers
from model.monte_carlo import run_simulation

app = FastAPI(
    title="F1 Race Predictor",
    description="Monte Carlo race prediction API for Formula 1",
    version="1.0.0"
)

# allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {
        "message": "F1 Race Predictor API",
        "endpoints": ["/chaos-coefficient", "/drivers", "/simulate"]
    }


@app.get("/chaos-coefficient")
def chaos():
    """Returns historical Shanghai chaos coefficient"""
    coefficient = get_chaos_coefficient()
    return {
        "circuit": "Shanghai International Circuit",
        "chaos_coefficient": round(coefficient, 3),
        "interpretation": "Average position change per driver per race"
    }


@app.get("/drivers")
def drivers():
    """Returns scored and ranked grid for 2026 Chinese GP"""
    raw = get_qualifying_results()
    scored = score_drivers(raw)
    return {
        "race": "2026 Chinese Grand Prix",
        "drivers": [
            {
                "rank": i + 1,
                "name": d["name"],
                "team": d["team"],
                "grid_position": d["grid_position"],
                "gap_to_pole": d["gap_to_pole"],
                "win_probability": d["win_probability"],
            }
            for i, d in enumerate(scored)
        ]
    }


@app.get("/simulate")
def simulate():
    """Runs Monte Carlo simulation and returns win and podium probabilities"""
    raw = get_qualifying_results()
    scored = score_drivers(raw)
    chaos = get_chaos_coefficient()
    results = run_simulation(scored, chaos)
    return {
        "race": "2026 Chinese Grand Prix",
        "simulations": 10000,
        "chaos_coefficient": round(chaos, 3),
        "predictions": [
            {
                "rank": i + 1,
                "name": d["name"],
                "team": d["team"],
                "grid_position": d["grid_position"],
                "win_probability": d["mc_win_probability"],
                "podium_probability": d["mc_podium_probability"],
            }
            for i, d in enumerate(results)
        ]
    }