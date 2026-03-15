import numpy as np

# Weights must sum to 1.0
WEIGHTS = {
    "grid_position":    0.35,
    "qualifying_pace":  0.25,
    "sprint_result":    0.15,
    "constructor_pace": 0.15,
    "shanghai_history": 0.10,
}

# Decay rates for exponential scoring
GRID_DECAY = 0.15   # how fast grid position advantage drops off
PACE_DECAY = 0.80   # how fast qualifying gap advantage drops off

def score_drivers(drivers):
    """
    Converts raw driver data into normalized win probabilty scores.
    Uses exponential decay for grip position and qualifying pace.
    Uses min-max normalization for sprint, constructor pace, history.
    Returns drivers list sorted by win probability descending.
    """
    
    if not drivers:
        return []

    #--- Step 1: Exponential decay scores--------------
    for driver in drivers:
        # grid position - P1 gets 1.0, decays expontentially
        driver["grid_score"] = np.exp(
            -GRID_DECAY * (driver["grid_position"] - 1)
        )

        # qualifying pace - pole gets 1.0, decays by gap in seconds
        driver["pace_score"] = np.exp(
            -PACE_DECAY * driver["gap_to_pole"]
        )

    #--- Step 2: Min-max normalization-----------------
    # sprint result — lower is better (P1 = best)
    sprint_positions = [d["sprint_result"] for d in drivers 
                        if d["sprint_result"] > 0]
    
    if sprint_positions:
        sprint_min = min(sprint_positions)
        sprint_max = max(sprint_positions)
        for driver in drivers:
            if driver["sprint_result"] > 0:
                driver["sprint_score"] = 1 - (
                    (driver["sprint_result"] - sprint_min) /
                    (sprint_max - sprint_min)
                )
            else:
                driver["sprint_score"] = 0.5  # no sprint data = neutral
    else:
        for driver in drivers:
            driver["sprint_score"] = 0.5  # no sprint this weekend = neutral

    # constructor pace — higher is better
    pace_values = [d["constructor_pace"] for d in drivers]
    pace_min = min(pace_values)
    pace_max = max(pace_values)
    for driver in drivers:
        driver["constructor_score"] = (
            (driver["constructor_pace"] - pace_min) /
            (pace_max - pace_min)
        )

    # shanghai history — higher is better
    history_values = [d["shanghai_history"] for d in drivers]
    history_min = min(history_values)
    history_max = max(history_values)
    for driver in drivers:
        driver["history_score"] = (
            (driver["shanghai_history"] - history_min) /
            (history_max - history_min)
        )
    
    # ── Step 3: Weighted sum → raw score ──────────────────────────
    for driver in drivers:
        driver["raw_score"] = (
            driver["grid_score"]        * WEIGHTS["grid_position"]    +
            driver["pace_score"]        * WEIGHTS["qualifying_pace"]  +
            driver["sprint_score"]      * WEIGHTS["sprint_result"]    +
            driver["constructor_score"] * WEIGHTS["constructor_pace"] +
            driver["history_score"]     * WEIGHTS["shanghai_history"]
        )

    # ── Step 4: Convert to win probabilities ──────────────────────
    total = sum(d["raw_score"] for d in drivers)
    for driver in drivers:
        driver["win_probability"] = round(driver["raw_score"] / total, 4)

    # ── Step 5: Sort by win probability descending ────────────────
    drivers.sort(key=lambda d: d["win_probability"], reverse=True)

    return drivers


if __name__ == "__main__":
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    
    from data.fetch_qualifying import get_qualifying_results
    
    drivers = get_qualifying_results()
    scored = score_drivers(drivers)
    
    print(f"\n2026 Chinese GP — Win Probability Predictions")
    print(f"{'Rank':<5} {'Driver':<20} {'Team':<20} {'Win %':>7} {'Grid':>5}")
    print("-" * 60)
    for i, driver in enumerate(scored, 1):
        print(f"{i:<5} "
              f"{driver['name']:<20} "
              f"{driver['team']:<20} "
              f"{driver['win_probability']*100:>6.2f}% "
              f"P{driver['grid_position']:>2}")