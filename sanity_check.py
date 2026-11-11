"""
sanity_check.py - verifies that the simulator's predicted attendance
                  never exceeds stadium capacity.

Runs a sample matchup, then cross-checks predicted attendance vs
the park_capacity table.
"""

import sys
import os
import sqlite3
import pandas as pd

# make sure we can import from the same directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from queries import AttendanceAnalyzer

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "baseball_attendance.db")

PASS = "  [PASS]"
FAIL = "  [FAIL]"
INFO = "  [INFO]"

def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def check_matchup(qa, home, vis, dow, daynight):
    """Run one simulation and validate the predicted attendance."""
    section(f"MATCHUP: {vis} at {home}  |  {dow} {daynight}")

    # --- 1. resolve park ---
    park_id = qa.get_park_id(home)
    capacity = qa.get_park_capacity(park_id) if park_id else None

    print(f"{INFO} Home team   : {home}")
    print(f"{INFO} Visitor     : {vis}")
    print(f"{INFO} Park ID     : {park_id or 'NOT FOUND'}")
    if capacity is not None:
        print(f"{INFO} Capacity    : {capacity:,} seats")
    else:
        print(f"{FAIL} No capacity on record for park '{park_id}' -- cannot cap-check")

    # --- 2. simulate attendance ---
    df = qa.simulate_attendance(home, vis, dow, daynight)

    if df.empty or pd.isna(df.iloc[0]["predicted_attendance"]):
        print(f"{FAIL} Simulator returned no prediction (insufficient data)")
        return False

    row = df.iloc[0]
    pred   = int(row["predicted_attendance"])
    lo     = int(row["low_estimate"])
    hi     = int(row["high_estimate"])
    level  = row["match_level"]
    n      = int(row["sample_size"])

    print(f"\n  Prediction Details")
    print(f"  {'Match level':<20}: {level} (n={n})")
    print(f"  {'Predicted attendance':<20}: {pred:,}")
    print(f"  {'Low estimate':<20}: {lo:,}")
    print(f"  {'High estimate':<20}: {hi:,}")

    # --- 3. cap check ---
    all_ok = True
    if capacity is not None:
        pct = pred / capacity * 100

        print(f"\n  Capacity Check")
        print(f"  {'Stadium capacity':<20}: {capacity:,}")
        print(f"  {'% full (predicted)':<20}: {pct:.1f}%")

        if pred > capacity:
            print(f"{FAIL} PREDICTED ({pred:,}) > CAPACITY ({capacity:,})  <- BUG!")
            all_ok = False
        else:
            print(f"{PASS} Predicted attendance is within capacity")

        if hi > capacity:
            print(f"  [WARN] High estimate ({hi:,}) exceeds capacity -- expected for historical max, not a bug")
        else:
            print(f"{PASS} High estimate is also within capacity")
    else:
        print(f"\n  Capacity Check: SKIPPED (no capacity data)")

    return all_ok


def check_capacity_table(qa):
    """Make sure every active MLB park has a capacity row."""
    section("PARK CAPACITY TABLE CHECK")

    with sqlite3.connect(DB_PATH) as conn:
        # parks that appear in recent games (2024+)
        active_parks = pd.read_sql_query(
            """
            SELECT DISTINCT g.park_id, p.park_name, p.city
            FROM games g
            JOIN parks p ON g.park_id = p.park_id
            WHERE g.season >= 2024
              AND g.gametype = 'regular'
            ORDER BY g.park_id
            """,
            conn
        )
        cap_df = pd.read_sql_query("SELECT park_id, seating_capacity FROM park_capacity", conn)

    merged = active_parks.merge(cap_df, on="park_id", how="left")
    missing = merged[merged["seating_capacity"].isna()]

    print(f"{INFO} Active parks (2024+)         : {len(active_parks)}")
    print(f"{INFO} Parks with capacity data     : {len(cap_df)}")

    if missing.empty:
        print(f"{PASS} All active parks have capacity data")
    else:
        print(f"{FAIL} {len(missing)} active park(s) missing capacity:")
        for _, r in missing.iterrows():
            print(f"       - {r['park_id']}  ({r['park_name']}, {r['city']})")

    # sanity: no capacity should be 0 or negative
    bad_cap = cap_df[cap_df["seating_capacity"] <= 0]
    if bad_cap.empty:
        print(f"{PASS} All capacity values are positive")
    else:
        print(f"{FAIL} Parks with zero/negative capacity: {bad_cap['park_id'].tolist()}")

    return missing.empty and bad_cap.empty


def check_historical_vs_capacity():
    """Find historical games where recorded attendance exceeded listed capacity."""
    section("HISTORICAL ATTENDANCE vs CAPACITY")

    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query(
            """
            SELECT g.game_id, g.game_date, g.home_team_id, g.park_id,
                   g.attendance, pc.seating_capacity,
                   ROUND(g.attendance * 100.0 / pc.seating_capacity, 1) AS pct_full
            FROM games g
            JOIN park_capacity pc ON g.park_id = pc.park_id
            WHERE g.gametype = 'regular'
              AND g.attendance IS NOT NULL
              AND g.attendance > pc.seating_capacity
            ORDER BY pct_full DESC
            LIMIT 10
            """,
            conn
        )

    if df.empty:
        print(f"{PASS} No historical games have attendance > capacity")
    else:
        print(f"  [WARN] {len(df)} historical game(s) exceeded listed capacity (standing room / data quirks):")
        print(df.to_string(index=False))
    return True


def main():
    print(f"\n{'='*60}")
    print("  BASEBALL SIMULATOR -- SANITY CHECK")
    print(f"{'='*60}\n")

    if not os.path.exists(DB_PATH):
        print(f"{FAIL} Database not found at {DB_PATH}")
        print("       Run `python db_setup.py` first.")
        sys.exit(1)

    qa = AttendanceAnalyzer(DB_PATH)

    results = []

    # --- test matchups ---
    test_cases = [
        # classic rivalry: Yankees at Boston
        ("BOS", "NYA", "Saturday", "day"),
        # Dodgers hosting Cubs -- big market showdown
        ("LAN", "CHN", "Friday",   "night"),
        # small-market team as home
        ("PIT", "CIN", "Tuesday",  "night"),
        # Rockies (Coors Field, highest capacity in NL)
        ("COL", "LAN", "Sunday",   "day"),
        # Texas Rangers at Globe Life Field (was missing capacity before)
        ("TEX", "HOU", "Friday",   "night"),
        # Cleveland (was missing capacity before)
        ("CLE", "NYA", "Saturday", "night"),
    ]

    for home, vis, dow, dn in test_cases:
        ok = check_matchup(qa, home, vis, dow, dn)
        results.append((f"{vis} at {home}", ok))

    # --- table / data checks ---
    cap_ok   = check_capacity_table(qa)
    hist_ok  = check_historical_vs_capacity()
    results.append(("Park capacity table complete", cap_ok))
    results.append(("Historical attendance vs capacity", hist_ok))

    # --- summary ---
    section("SUMMARY")
    all_passed = True
    for label, ok in results:
        status = PASS if ok else FAIL
        print(f"{status}  {label}")
        if not ok:
            all_passed = False

    print()
    if all_passed:
        print("  All checks passed.")
    else:
        print("  Some checks FAILED -- review output above.")
    print()


if __name__ == "__main__":
    main()

