import fastf1
import numpy as np
import os

cache_dir = os.path.join(os.path.dirname(__file__), '..', 'cache')
fastf1.Cache.enable_cache(cache_dir)

CHINESE_GP_YEARS = [
    2004, 2005, 2006, 2007, 2008, 2009, 2010,
    2011, 2012, 2013, 2014, 2015, 2016, 2017,
    2018, 2019, 2024, 2025
]

def get_chaos_coefficient():
    """
    Calculate average position change at Shanghai across all historical races.
    Higher = more chaotic circuit where grid position matters less.
    Lower = processional race where qualifying position is everything.
    """
    total_position_changes = []

    for year in CHINESE_GP_YEARS:
        try:
            print(f"Loading {year} Chinese GP...")
            session = fastf1.get_session(year, 'Chinese Grand Prix', 'R')
            session.load(telemetry=False, weather = False, messages=False)
            results = session.results

            if results is None or len(results) == 0:
                continue

            for _, driver in results.iterrows():
                grid = driver.get('GridPosition', None)
                finish = driver.get('Position', None)

                if grid and finish and grid > 0 and finish > 0:
                    change = abs(int(finish) - int(grid))
                    total_position_changes.append(change)
        except Exception as e:
            print(f" Skipping {year}: {e}")
            continue
    
    if len(total_position_changes) == 0:
        print("No data loaded - using default chaos coefficient")
        return 3.5

    coefficient = np.mean(total_position_changes)
    print(f"\nChaos coefficient: {coefficient: .2f}")
    print(f"Based on {len(total_position_changes)} driver results")
    return coefficient

if __name__ == "__main__":
    coef = get_chaos_coefficient()
    print(f"Final chaos coefficient: {coef:.2f}")