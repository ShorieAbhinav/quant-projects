import fastf1
import os

cache_dir = os.path.join(os.path.dirname(__file__), '..', 'cache')
fastf1.Cache.enable_cache(cache_dir)

# 2026 sprint race weekends
SPRINT_WEEKENDS = [
    'Chinese Grand Prix',
    'Belgian Grand Prix', 
    'United States Grand Prix',
    'Brazilian Grand Prix',
    'Qatar Grand Prix',
    'Austrian Grand Prix',
]

def get_sprint_results(year=2026, race='Chinese Grand Prix'):
    """
    Pulls sprint race results if this weekend has a sprint.
    Returns dict of {driver_full_name: finishing_position}
    Returns empty dict if no sprint weekend or data unavailable.
    """
    sprint_results = {}
    # check if this race has a sprint before even trying
    if race not in SPRINT_WEEKENDS:
        print(f"No sprint at {race} — skipping")
        return {}

    try:
        print(f"Fetching sprint results for {race}...")
        session = fastf1.get_session(year, race, 'Sprint')
        session.load(telemetry=False, weather=False, messages=False)
        results = session.results

        if results is None or len(results) == 0:
            print("No sprint data available")
            return {}

        sprint_dict = {}
        for _, driver in results.iterrows():
            name = driver.get('FullName', '')
            position = driver.get('Position', 0)
            if name and position:
                sprint_dict[name] = int(position)

        print(f"Sprint results loaded: {sprint_dict}")
        return sprint_dict

    except Exception as e:
        print(f"Sprint data unavailable: {e}")
        return {}

def get_constructor_pace(team_name):
    """
    Returns constructor pace rating 1-10 based on 2026 season form.
    Higher = faster car overall
    """

    pace_ratings = {
        "Mercedes":         9.5,
        "Ferrari":          8.5,
        "McLaren":          8.0,
        "Red Bull Racing":  7.0,
        "Haas F1 Team":     6.5,
        "Alpine":           6.0,
        "Racing Bulls":     6.0,
        "Audi":             5.5,
        "Williams":         5.0,
        "Aston Martin":     4.5,
        "Cadillac":         4.0,
    }
    return pace_ratings.get(team_name, 5.0)

def get_dnf_rate(team_name):
    """
    Returns historical DNF probability per race for each constructor.
    Based on 2024-2025 reliability date.
    """

    dnf_rates = {
        "Mercedes":         0.06,
        "Ferrari":          0.07,
        "McLaren":          0.05,
        "Red Bull Racing":  0.08,
        "Haas F1 Team":     0.09,
        "Alpine":           0.09,
        "Racing Bulls":     0.08,
        "Audi":             0.10,
        "Williams":         0.08,
        "Aston Martin":     0.09,
        "Cadillac":         0.11,
    }
    return dnf_rates.get(team_name, 0.08)

def get_shanghai_history(driver_name):
    """
    Returns driver's Shanghai track history score 1-10.
    Based on historical wins, podiums and familiarity with circuit.
    Rookies and drivers with no Shanghai history score low.
    """
    history_scores = {
        # Multiple wins at Shanghai
        "Lewis Hamilton":       9.0,
        "Fernando Alonso":      8.0,
        "Michael Schumacher":   9.0,
        "Sebastian Vettel":     8.5,
        "Max Verstappen":       8.0,
        # Podiums and strong results
        "George Russell":       7.0,
        "Valtteri Bottas":      6.0,
        "Carlos Sainz":         6.0,
        "Charles Leclerc":      6.0,
        "Lando Norris":         6.0,
        "Pierre Gasly":         5.0,
        "Esteban Ocon":         4.0,
        "Lance Stroll":         4.0,
        "Alexander Albon":      4.0,
        "Sergio Perez":         5.0,
        "Nico Hulkenberg":      5.0,
        # Limited Shanghai history
        "Oscar Piastri":        5.0,
        "Liam Lawson":          3.0,
        "Oliver Bearman":       3.0,
        "Franco Colapinto":     2.0,
        # Rookies — no Shanghai history
        "Kimi Antonelli":       5.0,
        "Isack Hadjar":         3.0,
        "Arvid Lindblad":       1.0,
        "Gabriel Bortoleto":    1.0,
    }
    return history_scores.get(driver_name, 3.0)

def get_qualifying_results(year=2026, race='Chinese Grand Prix'):
    """
    Pulls qualifying results for any race from FastF1 API.
    Returns list of driver dicts with grid position, gap to pole,
    team, and quali time.
    Falls back to None if session not available yet.
    """
    sprint_results = {}
    try:
        print(f"Fetching {year} {race} qualifying data...")
        session = fastf1.get_session(year, race, 'Q')
        session.load(telemetry=False, weather=False, messages=False)
        results = session.results

        if results is None or len(results) == 0:
            print("No qualifying data available")
            return None

        # pole time in seconds for gap calculation
        pole_time = results.iloc[0]['Q3']
        if hasattr(pole_time, 'total_seconds'):
            pole_seconds = pole_time.total_seconds()
        else:
            pole_seconds = float(pole_time)

        # Pull sprint results ONCE before the loop
        sprint_results = get_sprint_results(year, race)

        drivers = []
        for position, (_, driver) in enumerate(results.iterrows(), start=1):
            # get best qualifying time across Q1/Q2/Q3
            best_time = None
            for q in ['Q3', 'Q2', 'Q1']:
                t = driver.get(q)
                if t is not None and str(t) != 'NaT':
                    best_time = t
                    break

            if best_time is not None and hasattr(best_time, 'total_seconds'):
                quali_seconds = best_time.total_seconds()
            else:
                # fallback if time not available
                quali_seconds = pole_seconds + (position * 0.5)

            gap = quali_seconds - pole_seconds

            drivers.append({
                "grid_position": position,
                "name": driver.get('FullName', driver.get('Abbreviation', 'Unknown')),
                "team": driver.get('TeamName', 'Unknown'),
                "quali_time": round(quali_seconds, 3),
                "gap_to_pole": round(gap, 3),
                "constructor_pace": get_constructor_pace(driver.get('TeamName', '')),
                "shanghai_history": get_shanghai_history(driver.get('FullName', '')),
                "sprint_result": sprint_results.get(driver.get('FullName', ''), 0),
                "dnf_rate": get_dnf_rate(driver.get('TeamName', '')),
            })

        print(f"Successfully loaded {len(drivers)} drivers")
        return drivers

    except Exception as e:
        print(f"Failed to fetch qualifying data: {e}")
        return None

if __name__ == "__main__":
    drivers = get_qualifying_results()
    
    if drivers:
        print(f"\n2026 Chinese GP Starting Grid:")
        print(f"{'Pos':<4} {'Driver':<20} {'Team':<20} {'Gap':>8}")
        print("-" * 55)
        for driver in drivers:
            print(f"P{driver['grid_position']:<3} "
                  f"{driver['name']:<20} "
                  f"{driver['team']:<20} "
                  f"+{driver['gap_to_pole']:.3f}s")
    else:
        print("No data available")

