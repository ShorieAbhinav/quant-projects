import numpy as np

# Number of races to simulate
N_SIMULATIONS = 10000

# Safety car probability at Shanghai
SAFETY_CAR_PROBABILITY = 0.35

# How much safety car compresses the field
SAFETY_CAR_COMPRESSION = 0.4

def run_simulation(scored_drivers, chaos_coefficient):
    """
    Runs N_SIMULATIONS Monte Carlo race simulations.
    Each simulation:
    1. Starts drivers at their grid positions
    2. Injects random position noise scaled by chaos coefficient
    3. Applies DNF probability per team
    4. Applies safety car randomness
    5. Counts wins and podiums across all simulations

    Returns drivers list with win_probability and podium_probability added.
    """
    if not scored_drivers:
        return []

    n_drivers = len(scored_drivers)
    
    # track wins and podiums across all simulations
    win_counts    = {d["name"]: 0 for d in scored_drivers}
    podium_counts = {d["name"]: 0 for d in scored_drivers}

    for sim in range(N_SIMULATIONS):
        # ── Start with baseline win probabilities as weights ───────
        weights = [d["win_probability"] for d in scored_drivers]
         
        # ── Inject chaos — random position noise ───────────────────
        safety_car = np.random.random() < SAFETY_CAR_PROBABILITY
        
        if safety_car:
            noise_scale = chaos_coefficient * SAFETY_CAR_COMPRESSION
        else:
            noise_scale = chaos_coefficient
        
        # add random noise to each driver's weight
        noise = np.random.normal(0, noise_scale * 0.01, n_drivers)
        weights = [max(0, w + n) for w, n in zip(weights, noise)]
        
        # ── Apply DNF probability ──────────────────────────────────
        dnf_mask = [
            np.random.random() < d["dnf_rate"] 
            for d in scored_drivers
        ]
        
        # zero out DNF drivers
        weights = [0 if dnf else w 
                   for w, dnf in zip(weights, dnf_mask)]
        
        # ── Pick race result ───────────────────────────────────────
        total = sum(weights)
        if total == 0:
            continue
            
        probabilities = [w / total for w in weights]

        # count non-zero probabilties
        non_zero = sum(1 for p in probabilities if p > 0) 
        
        # only as many positions as we have active drivers
        finishing_order = np.random.choice(
            n_drivers,
            size=non_zero,
            replace=False,
            p=probabilities
        )
        
        # ── Record results ─────────────────────────────────────────
        winner = scored_drivers[finishing_order[0]]["name"]
        win_counts[winner] += 1
        
        for pos in range(min(3, n_drivers)):
            podium_driver = scored_drivers[finishing_order[pos]]["name"]
            podium_counts[podium_driver] += 1
        
    # ── Convert counts to probabilities ───────────────────────────
    for driver in scored_drivers:
        name = driver["name"]
        driver["mc_win_probability"] = round(
            win_counts[name] / N_SIMULATIONS, 4
        )
        driver["mc_podium_probability"] = round(
            podium_counts[name] / N_SIMULATIONS, 4
        )

    # sort by Monte Carlo win probability
    scored_drivers.sort(
        key=lambda d: d["mc_win_probability"], 
        reverse=True
    )

    return scored_drivers


if __name__ == "__main__":
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

    from data.fetch_qualifying import get_qualifying_results
    from data.fetch_historical import get_chaos_coefficient
    from model.scorer import score_drivers

    print("Loading data...")
    drivers = get_qualifying_results()
    scored = score_drivers(drivers)
    chaos = get_chaos_coefficient()

    print(f"\nRunning {N_SIMULATIONS} simulations...")
    results = run_simulation(scored, chaos)

    print(f"\n2026 Chinese GP — Monte Carlo Predictions")
    print(f"{'Rank':<5} {'Driver':<20} {'Win %':>7} {'Podium %':>9} {'Grid':>5}")
    print("-" * 55)
    for i, driver in enumerate(results, 1):
        print(f"{i:<5} "
              f"{driver['name']:<20} "
              f"{driver['mc_win_probability']*100:>6.2f}% "
              f"{driver['mc_podium_probability']*100:>8.2f}% "
              f"P{driver['grid_position']:>2}")