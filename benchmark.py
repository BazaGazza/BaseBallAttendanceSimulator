import sqlite3
import time

DB_PATH = 'baseball_attendance.db'

QUERIES_TO_BENCHMARK = [
    {
        "name": "Matchup Prediction Query",
        "sql": "SELECT COUNT(*), AVG(attendance) FROM games WHERE home_team_id = 'BOS' AND vis_team_id = 'NYA' AND day_of_week = 'Saturday' AND daynight = 'night'"
    },
    {
        "name": "Weather Impact Query",
        "sql": "SELECT * FROM v_weather_impact WHERE home_team_id = 'BOS'"
    },
    {
        "name": "Day of Week Impact Query",
        "sql": "SELECT * FROM v_day_of_week_effects WHERE home_team_id = 'BOS'"
    },
    {
        "name": "Ticket Pricing Unified Query",
        "sql": "SELECT COUNT(*), AVG(floor_price) FROM v_ticket_pricing WHERE home_team_id = 'BOS' AND vis_team_id = 'NYA'"
    }
]

INDEXES_TO_TOGGLE = [
    "idx_games_team_dow",
    "idx_games_team_daynight",
    "idx_games_team_weather",
    "idx_gt_team_matchup",
    "idx_sg_team_matchup"
]

INDEX_DDL = [
    "CREATE INDEX IF NOT EXISTS idx_games_team_dow ON games(home_team_id, day_of_week);",
    "CREATE INDEX IF NOT EXISTS idx_games_team_daynight ON games(home_team_id, daynight);",
    "CREATE INDEX IF NOT EXISTS idx_games_team_weather ON games(home_team_id, sky, precip);",
    "CREATE INDEX IF NOT EXISTS idx_gt_team_matchup ON gametime_events(home_team_id, vis_team_id);",
    "CREATE INDEX IF NOT EXISTS idx_sg_team_matchup ON seatgeek_events(home_team_id, vis_team_id);"
]

def run_benchmark(label):
    print(f"\n{'-'*60}")
    print(f"  BENCHMARK: {label}")
    print(f"{'-'*60}")
    
    with sqlite3.connect(DB_PATH) as conn:
        for q in QUERIES_TO_BENCHMARK:
            start_time = time.time()
            for _ in range(100):  # run it 100 times so the timer actually catches something
                conn.execute(q['sql']).fetchall()
            elapsed_ms = (time.time() - start_time) * 1000
            print(f"{q['name']:<35}: {elapsed_ms:,.2f} ms")

if __name__ == "__main__":
    print("="*60)
    print("  SIMULATOR QUERY PERFORMANCE BENCHMARKING")
    print("="*60)
    
    # step 1: test the current database that has all our indexes
    run_benchmark("WITH INDEXES (Current State)")
    
    # step 2: delete the indexes to see how slow it gets
    with sqlite3.connect(DB_PATH) as conn:
        for idx in INDEXES_TO_TOGGLE:
            conn.execute(f"DROP INDEX IF EXISTS {idx}")
        conn.commit()
        
    # step 3: test again but without the indexes
    run_benchmark("WITHOUT INDEXES")
    
    # step 4: put the indexes back so we don't break the main app
    with sqlite3.connect(DB_PATH) as conn:
        for ddl in INDEX_DDL:
            conn.execute(ddl)
        conn.commit()
        
    print("\n[OK] Benchmarking complete, indexes restored.")
