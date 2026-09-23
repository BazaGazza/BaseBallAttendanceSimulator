"""
[PROTOTYPE] db_setup.py — Load CSV data into a SQLite database with proper relational schema.

Creates `baseball_attendance.db` with three tables:
  - parks       (from clean_parks.csv)
  - teams       (from clean_teams.csv)
  - games       (from clean_games.csv) with foreign keys to parks & teams

Usage:
    python db_setup.py            # builds the DB from CSVs in the same directory
    python db_setup.py --force    # drops & rebuilds even if the DB already exists
"""

import argparse
import os
import sqlite3
import sys

import pandas as pd

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DB_NAME = "baseball_attendance.db"
DATA_DIR = os.path.dirname(os.path.abspath(__file__))

CSV_FILES = {
    "parks": os.path.join(DATA_DIR, "clean_parks.csv"),
    "teams": os.path.join(DATA_DIR, "clean_teams.csv"),
    "games": os.path.join(DATA_DIR, "clean_games.csv"),
}

# ---------------------------------------------------------------------------
# Schema DDL
# ---------------------------------------------------------------------------
SCHEMA_SQL = """
-- Enable foreign-key enforcement (off by default in SQLite)
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS parks (
    park_id     TEXT PRIMARY KEY,
    park_name   TEXT,
    aka         TEXT,
    city        TEXT,
    state       TEXT,
    start_date  TEXT,
    end_date    TEXT,
    league      TEXT,
    notes       TEXT
);

CREATE TABLE IF NOT EXISTS teams (
    team_id TEXT PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS games (
    game_id       TEXT PRIMARY KEY,
    game_date     TEXT NOT NULL,
    season        INTEGER NOT NULL,
    day_of_week   TEXT NOT NULL,
    park_id       TEXT,
    home_team_id  TEXT,
    vis_team_id   TEXT,
    attendance    INTEGER,
    daynight      TEXT,
    temp          REAL,
    sky           TEXT,
    precip        TEXT,
    wind_dir      TEXT,
    wind_speed    REAL,
    field_cond    TEXT,
    home_runs     INTEGER,
    vis_runs      INTEGER,
    total_runs    INTEGER,
    gametype      TEXT,
    FOREIGN KEY (park_id)      REFERENCES parks(park_id),
    FOREIGN KEY (home_team_id) REFERENCES teams(team_id),
    FOREIGN KEY (vis_team_id)  REFERENCES teams(team_id)
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_games_season      ON games(season);
CREATE INDEX IF NOT EXISTS idx_games_home_team   ON games(home_team_id);
CREATE INDEX IF NOT EXISTS idx_games_park        ON games(park_id);
CREATE INDEX IF NOT EXISTS idx_games_date        ON games(game_date);
CREATE INDEX IF NOT EXISTS idx_games_daynight    ON games(daynight);
CREATE INDEX IF NOT EXISTS idx_games_gametype    ON games(gametype);
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _clean_nulls(df: pd.DataFrame) -> pd.DataFrame:
    """Replace pandas NA values with None so sqlite stores real NULLs."""
    return df.where(df.notna(), None)


def build_database(db_path: str, force: bool = False) -> None:
    """Create the SQLite database and populate it from CSVs."""

    if os.path.exists(db_path):
        if force:
            os.remove(db_path)
            print(f"  [*] Removed existing database: {db_path}")
        else:
            print(f"  [OK] Database already exists: {db_path}")
            print("     Use --force to rebuild from scratch.")
            return

    # Verify CSV files exist
    for name, path in CSV_FILES.items():
        if not os.path.isfile(path):
            print(f"  [ERR] Missing CSV: {path}")
            sys.exit(1)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Create schema
    cur.executescript(SCHEMA_SQL)
    print("  [OK] Schema created")

    # --- Parks ---
    parks_df = _clean_nulls(pd.read_csv(CSV_FILES["parks"]))
    parks_df.to_sql("parks", conn, if_exists="append", index=False)
    print(f"  [OK] Loaded {len(parks_df):,} parks")

    # --- Teams ---
    teams_df = _clean_nulls(pd.read_csv(CSV_FILES["teams"]))
    teams_df.to_sql("teams", conn, if_exists="append", index=False)
    print(f"  [OK] Loaded {len(teams_df):,} teams")

    # --- Games ---
    games_df = _clean_nulls(pd.read_csv(CSV_FILES["games"]))
    games_df.to_sql("games", conn, if_exists="append", index=False)
    print(f"  [OK] Loaded {len(games_df):,} games")

    conn.commit()

    # Quick sanity check
    row_counts = {}
    for table in ("parks", "teams", "games"):
        (count,) = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
        row_counts[table] = count
    print(f"\n  Database summary:")
    for table, count in row_counts.items():
        print(f"    {table:>6}: {count:>8,} rows")

    conn.close()
    print(f"\n  [OK] Database saved to {db_path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Build the baseball attendance SQLite database from CSVs."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Drop and rebuild the database even if it already exists.",
    )
    args = parser.parse_args()

    db_path = os.path.join(DATA_DIR, DB_NAME)
    print(f"\n{'='*60}")
    print("  Baseball Attendance — Database Builder")
    print(f"{'='*60}\n")
    build_database(db_path, force=args.force)
    print()


if __name__ == "__main__":
    main()
