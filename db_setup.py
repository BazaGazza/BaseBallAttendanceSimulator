"""
db_setup.py - loads csv data into sqlite database

this creates baseball_attendance.db and sets up all our tables and views
so the simulator can use it.

how to use:
    python db_setup.py            # builds the db from csvs
    python db_setup.py --force    # deletes the old db and builds a new one
"""

import argparse
import os
import re
import sqlite3
import sys

import pandas as pd

# ---------------------------------------------------------------------------
# config setup
# ---------------------------------------------------------------------------
DB_NAME = "baseball_attendance.db"
DATA_DIR = os.path.dirname(os.path.abspath(__file__))

CSV_FILES = {
    "parks": os.path.join(DATA_DIR, "clean_parks.csv"),
    "teams": os.path.join(DATA_DIR, "clean_teams.csv"),
    "games": os.path.join(DATA_DIR, "clean_games.csv"),
    "gametime": os.path.join(DATA_DIR, "clean_gametime.csv"),
    "seatgeek": os.path.join(DATA_DIR, "clean_seatgeek.csv"),
}

# ---------------------------------------------------------------------------
# sql schema
# ---------------------------------------------------------------------------
SCHEMA_SQL = """
-- turn on foreign keys so we don't get bad data
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

-- add indexes to make common queries faster
CREATE INDEX IF NOT EXISTS idx_games_season      ON games(season);
CREATE INDEX IF NOT EXISTS idx_games_home_team   ON games(home_team_id);
CREATE INDEX IF NOT EXISTS idx_games_park        ON games(park_id);
CREATE INDEX IF NOT EXISTS idx_games_date        ON games(game_date);
CREATE INDEX IF NOT EXISTS idx_games_daynight    ON games(daynight);
CREATE INDEX IF NOT EXISTS idx_games_gametype    ON games(gametype);

-- -----------------------------------------------------------------------
-- tables for the ticket websites
-- -----------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS team_lookup (
    team_id    TEXT PRIMARY KEY REFERENCES teams(team_id),
    full_name  TEXT NOT NULL,
    city       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS venue_map (
    park_id        TEXT PRIMARY KEY REFERENCES parks(park_id),
    gt_venue_id    TEXT UNIQUE,
    sg_venue_id    INTEGER UNIQUE,
    venue_name     TEXT
);

CREATE TABLE IF NOT EXISTS gametime_events (
    event_id         TEXT PRIMARY KEY,
    event_name       TEXT NOT NULL,
    event_date       TEXT NOT NULL,
    park_id          TEXT REFERENCES parks(park_id),
    home_team_id     TEXT REFERENCES teams(team_id),
    vis_team_id      TEXT REFERENCES teams(team_id),
    min_price        INTEGER,
    max_price        INTEGER,
    trending_score   REAL,
    source_venue_id  TEXT
);

CREATE TABLE IF NOT EXISTS seatgeek_events (
    event_id          INTEGER PRIMARY KEY,
    event_name        TEXT NOT NULL,
    event_date        TEXT NOT NULL,
    park_id           TEXT REFERENCES parks(park_id),
    home_team_id      TEXT REFERENCES teams(team_id),
    vis_team_id       TEXT REFERENCES teams(team_id),
    event_score       REAL,
    popularity_score  REAL,
    listing_count     INTEGER,
    ticket_count      INTEGER,
    avg_price         INTEGER,
    lowest_price      INTEGER,
    highest_price     INTEGER,
    source_venue_id   INTEGER
);

-- indexes for the ticket events
CREATE INDEX IF NOT EXISTS idx_gt_home_team   ON gametime_events(home_team_id);
CREATE INDEX IF NOT EXISTS idx_gt_event_date  ON gametime_events(event_date);
CREATE INDEX IF NOT EXISTS idx_gt_park        ON gametime_events(park_id);

CREATE INDEX IF NOT EXISTS idx_sg_home_team   ON seatgeek_events(home_team_id);
CREATE INDEX IF NOT EXISTS idx_sg_event_date  ON seatgeek_events(event_date);
CREATE INDEX IF NOT EXISTS idx_sg_park        ON seatgeek_events(park_id);

-- view that puts gametime and seatgeek prices together
CREATE VIEW IF NOT EXISTS v_ticket_pricing AS
SELECT
    event_id,
    event_name,
    event_date,
    park_id,
    home_team_id,
    vis_team_id,
    min_price / 100.0 AS floor_price,
    max_price / 100.0 AS ceiling_price,
    NULL            AS avg_price,
    trending_score  AS demand_score,
    NULL            AS listing_count,
    NULL            AS ticket_count,
    'gametime'      AS source
FROM gametime_events
UNION ALL
SELECT
    CAST(event_id AS TEXT),
    event_name,
    event_date,
    park_id,
    home_team_id,
    vis_team_id,
    lowest_price,
    highest_price,
    avg_price,
    popularity_score,
    listing_count,
    ticket_count,
    'seatgeek'
FROM seatgeek_events;

-- -----------------------------------------------------------------------
-- analytical views for the simulator
-- -----------------------------------------------------------------------

-- view for pre-aggregated attendance stats per team
CREATE VIEW IF NOT EXISTS v_team_attendance_stats AS
SELECT 
    home_team_id,
    season,
    COUNT(*) AS games_played,
    ROUND(AVG(attendance)) AS avg_attendance,
    MIN(attendance) AS min_attendance,
    MAX(attendance) AS max_attendance
FROM games
WHERE gametype = 'regular' AND attendance IS NOT NULL
GROUP BY home_team_id, season;

-- view for historical attendance for every home/visitor pair
CREATE VIEW IF NOT EXISTS v_matchup_history AS
SELECT
    home_team_id,
    vis_team_id,
    COUNT(*) AS games_played,
    ROUND(AVG(attendance)) AS avg_attendance,
    MIN(attendance) AS min_attendance,
    MAX(attendance) AS max_attendance
FROM games
WHERE gametype = 'regular' AND attendance IS NOT NULL
GROUP BY home_team_id, vis_team_id;

-- view for day-of-week attendance multipliers per team
CREATE VIEW IF NOT EXISTS v_day_of_week_effects AS
WITH team_baseline AS (
    SELECT home_team_id, AVG(attendance) AS baseline_avg
    FROM games
    WHERE gametype = 'regular' AND attendance IS NOT NULL
    GROUP BY home_team_id
),
dow_avg AS (
    SELECT home_team_id, day_of_week, AVG(attendance) AS dow_avg
    FROM games
    WHERE gametype = 'regular' AND attendance IS NOT NULL
    GROUP BY home_team_id, day_of_week
)
SELECT 
    d.home_team_id,
    d.day_of_week,
    ROUND(d.dow_avg) AS avg_attendance,
    ROUND(d.dow_avg - b.baseline_avg) AS impact_vs_baseline
FROM dow_avg d
JOIN team_baseline b ON d.home_team_id = b.home_team_id;

-- view for weather impact
CREATE VIEW IF NOT EXISTS v_weather_impact AS
WITH team_baseline AS (
    SELECT home_team_id, AVG(attendance) AS baseline_avg
    FROM games
    WHERE gametype = 'regular' AND attendance IS NOT NULL
    GROUP BY home_team_id
),
weather_avg AS (
    SELECT 
        home_team_id, 
        sky, 
        precip,
        CASE 
            WHEN temp < 60 THEN 'Cold'
            WHEN temp >= 60 AND temp <= 85 THEN 'Moderate'
            ELSE 'Hot'
        END AS temp_bucket,
        AVG(attendance) AS weather_avg,
        COUNT(*) AS sample_size
    FROM games
    WHERE gametype = 'regular' AND attendance IS NOT NULL
    GROUP BY home_team_id, sky, precip, temp_bucket
)
SELECT 
    w.home_team_id,
    w.sky,
    w.precip,
    w.temp_bucket,
    ROUND(w.weather_avg) AS avg_attendance,
    ROUND(w.weather_avg - b.baseline_avg) AS impact_vs_baseline,
    w.sample_size
FROM weather_avg w
JOIN team_baseline b ON w.home_team_id = b.home_team_id;

-- -----------------------------------------------------------------------
-- composite indexes for simulator queries
-- -----------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_games_team_dow ON games(home_team_id, day_of_week);
CREATE INDEX IF NOT EXISTS idx_games_team_daynight ON games(home_team_id, daynight);
CREATE INDEX IF NOT EXISTS idx_games_team_weather ON games(home_team_id, sky, precip);
CREATE INDEX IF NOT EXISTS idx_gt_team_matchup ON gametime_events(home_team_id, vis_team_id);
CREATE INDEX IF NOT EXISTS idx_sg_team_matchup ON seatgeek_events(home_team_id, vis_team_id);
"""


# ---------------------------------------------------------------------------
# Static lookup data — 30 current MLB teams
# ---------------------------------------------------------------------------
# match the full team names to their short ids
# the city column just helps us read it easier
TEAM_LOOKUP_DATA = [
    # (team_id, full_name, city)
    ("ARI", "Arizona Diamondbacks", "Arizona"),
    ("ATL", "Atlanta Braves", "Atlanta"),
    ("BAL", "Baltimore Orioles", "Baltimore"),
    ("BOS", "Boston Red Sox", "Boston"),
    ("CHN", "Chicago Cubs", "Chicago"),
    ("CHA", "Chicago White Sox", "Chicago"),
    ("CIN", "Cincinnati Reds", "Cincinnati"),
    ("CLE", "Cleveland Guardians", "Cleveland"),
    ("COL", "Colorado Rockies", "Colorado"),
    ("DET", "Detroit Tigers", "Detroit"),
    ("HOU", "Houston Astros", "Houston"),
    ("KCA", "Kansas City Royals", "Kansas City"),
    ("ANA", "Los Angeles Angels", "Los Angeles"),
    ("LAN", "Los Angeles Dodgers", "Los Angeles"),
    ("MIA", "Miami Marlins", "Miami"),
    ("MIL", "Milwaukee Brewers", "Milwaukee"),
    ("MIN", "Minnesota Twins", "Minnesota"),
    ("NYN", "New York Mets", "New York"),
    ("NYA", "New York Yankees", "New York"),
    ("ATH", "Athletics", "Sacramento"),
    ("PHI", "Philadelphia Phillies", "Philadelphia"),
    ("PIT", "Pittsburgh Pirates", "Pittsburgh"),
    ("SDN", "San Diego Padres", "San Diego"),
    ("SFN", "San Francisco Giants", "San Francisco"),
    ("SEA", "Seattle Mariners", "Seattle"),
    ("SLN", "St. Louis Cardinals", "St. Louis"),
    ("TBA", "Tampa Bay Rays", "Tampa Bay"),
    ("TEX", "Texas Rangers", "Texas"),
    ("TOR", "Toronto Blue Jays", "Toronto"),
    ("WAS", "Washington Nationals", "Washington"),
]

# link each team to their home stadium and ticket website ids
VENUE_MAP_DATA = [
    # (park_id, gt_venue_id, sg_venue_id, venue_name)
    ("PHO01", "538526c421efd33afb000006", 30, "Chase Field"),
    ("ATL03", "5876a1f7cde6626ebe0d3e87", 418889, "Truist Park"),
    ("BAL12", "53bb068c3bf37624c3000004", 25, "Oriole Park at Camden Yards"),
    ("BOS07", "5362ccf73bf37627c6000001", 21, "Fenway Park"),
    ("CHI11", "533d97153bf3766542000002", 11, "Wrigley Field"),
    ("CHI12", "5362ccf73bf37627c6000004", 3715, "Guaranteed Rate Field"),
    ("CIN09", "53beec013bf376503f000001", 26, "Great American Ballpark"),
    ("CLE08", "53beec013bf376503f000002", 6, "Progressive Field"),
    ("DEN02", "53acb8a23bf3760237000006", 7, "Coors Field"),
    ("DET05", "53c03a3b3bf37612c4000002", 12, "Comerica Park"),
    ("HOU03", "53b30c243bf37646fb000002", 20, "Minute Maid Park"),
    ("KAN06", "538526c321efd33afb000004", 3714, "Kauffman Stadium"),
    ("ANA01", "533d97153bf3766542000001", 28, "Angel Stadium"),
    ("LOS03", "5333a2763bf3767900000001", 1, "Dodger Stadium"),
    ("MIA02", "53acb8a23bf3760237000004", 6371, "loanDepot Park"),
    ("MIL06", "538526c321efd33afb000003", 15, "American Family Field"),
    ("MIN04", "538526c321efd33afb000005", 3712, "Target Field"),
    ("NYC20", "5362ccf73bf37627c6000002", 3, "Citi Field"),
    ("NYC21", "5362ccf73bf37627c6000003", 8, "Yankee Stadium"),
    ("SAC01", "55313d1878fea568e6000001", 317, "Sutter Health Park"),
    ("PHI13", "539619523bf37601f6000001", 18, "Citizens Bank Park"),
    ("PIT08", "538526c321efd33afb000002", 10, "PNC Park"),
    ("SAN02", "53692f0a3bf3760f90000001", 24, "Petco Park"),
    ("SFO03", "52618c753bf3760b9c000004", 22, "Oracle Park"),
    ("SEA03", "538526c321efd33afb000001", 13, "T-Mobile Park"),
    ("STL10", "54b5ab3b3bf3763f85000001", 27, "Busch Stadium"),
    ("TAM02", "54dcf29564f9620805000003", 4, "George M. Steinbrenner Field"),
    ("ARL03", "5d9f4ea483e7d2003a7aa81a", 487468, "Globe Life Field"),
    ("TOR02", "55116f6864f9625eb3000001", 17, "Rogers Centre"),
    ("WAS11", "5388f0613bf3761afd000002", 3713, "Nationals Park"),
]


# ---------------------------------------------------------------------------
# helper functions
# ---------------------------------------------------------------------------
def _clean_nulls(df: pd.DataFrame) -> pd.DataFrame:
    """change pandas missing values to none so the db stores nulls correctly"""
    return df.where(df.notna(), None)


# use regex to figure out who is playing who from strings like "visitor at home"
_NAME_PATTERN = re.compile(r"^(.+?)\s+at\s+(.+?)(?:\s*\(.*)?$")


def _build_name_to_id(team_data: list[tuple]) -> dict[str, str]:
    """make a dictionary to look up team ids from full names"""
    return {full_name: team_id for team_id, full_name, _ in team_data}


def _parse_event_name(name: str, name_to_id: dict[str, str]) -> tuple:
    """
    read an event name like "pittsburgh pirates at new york mets"
    and spit out the team ids for the visitor and home teams.

    returns (none, none) if it can't figure it out.
    """
    m = _NAME_PATTERN.match(name)
    if not m:
        return None, None

    vis_name = m.group(1).strip()
    home_name = m.group(2).strip()

    # check for an exact match first
    vis_id = name_to_id.get(vis_name)
    home_id = name_to_id.get(home_name)

    # if it doesn't match exactly, try matching the start of the name
    if vis_id is None:
        for full_name, tid in name_to_id.items():
            if vis_name.startswith(full_name):
                vis_id = tid
                break
    if home_id is None:
        for full_name, tid in name_to_id.items():
            if home_name.startswith(full_name):
                home_id = tid
                break

    return vis_id, home_id


def _build_venue_lookups(venue_data: list[tuple]) -> tuple[dict, dict]:
    """make dictionaries to match ticket websites to stadiums"""
    gt_to_park = {gt_vid: park_id for park_id, gt_vid, _, _ in venue_data}
    sg_to_park = {sg_vid: park_id for park_id, _, sg_vid, _ in venue_data}
    return gt_to_park, sg_to_park


# ---------------------------------------------------------------------------
# database builder
# ---------------------------------------------------------------------------
def build_database(db_path: str, force: bool = False) -> None:
    """create the database and dump all the csv data into it"""

    if os.path.exists(db_path):
        if force:
            os.remove(db_path)
            print(f"  [*] Removed existing database: {db_path}")
        else:
            print(f"  [OK] Database already exists: {db_path}")
            print("     Use --force to rebuild from scratch.")
            return

    # make sure we have all our csv files
    for name, path in CSV_FILES.items():
        if not os.path.isfile(path):
            print(f"  [ERR] Missing CSV: {path}")
            sys.exit(1)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # ------------------------------------------------------------------
    # create the tables and stuff
    # ------------------------------------------------------------------
    cur.executescript(SCHEMA_SQL)
    print("  [OK] Schema created")

    # ------------------------------------------------------------------
    # dump in the old retrosheet data
    # ------------------------------------------------------------------
    parks_df = _clean_nulls(pd.read_csv(CSV_FILES["parks"]))
    parks_df.to_sql("parks", conn, if_exists="append", index=False)
    print(f"  [OK] Loaded {len(parks_df):,} parks")

    teams_df = _clean_nulls(pd.read_csv(CSV_FILES["teams"]))
    teams_df.to_sql("teams", conn, if_exists="append", index=False)
    print(f"  [OK] Loaded {len(teams_df):,} teams")

    games_df = _clean_nulls(pd.read_csv(CSV_FILES["games"]))
    games_df.to_sql("games", conn, if_exists="append", index=False)
    print(f"  [OK] Loaded {len(games_df):,} games")

    # ------------------------------------------------------------------
    # dump in the team lookups
    # ------------------------------------------------------------------
    # make sure all our teams actually exist in the db first
    existing_teams = set(
        row[0] for row in cur.execute("SELECT team_id FROM teams").fetchall()
    )
    for team_id, _, _ in TEAM_LOOKUP_DATA:
        if team_id not in existing_teams:
            cur.execute("INSERT INTO teams (team_id) VALUES (?)", (team_id,))
            existing_teams.add(team_id)

    for team_id, full_name, city in TEAM_LOOKUP_DATA:
        cur.execute(
            "INSERT INTO team_lookup (team_id, full_name, city) VALUES (?, ?, ?)",
            (team_id, full_name, city),
        )
    print(f"  [OK] Loaded {len(TEAM_LOOKUP_DATA)} team lookups")

    # ------------------------------------------------------------------
    # dump in the venue mappings
    # ------------------------------------------------------------------
    for park_id, gt_vid, sg_vid, venue_name in VENUE_MAP_DATA:
        cur.execute(
            "INSERT INTO venue_map (park_id, gt_venue_id, sg_venue_id, venue_name) "
            "VALUES (?, ?, ?, ?)",
            (park_id, gt_vid, sg_vid, venue_name),
        )
    print(f"  [OK] Loaded {len(VENUE_MAP_DATA)} venue mappings")

    # ------------------------------------------------------------------
    # setup our lookup tools so we can parse the names later
    # ------------------------------------------------------------------
    name_to_id = _build_name_to_id(TEAM_LOOKUP_DATA)
    gt_to_park, sg_to_park = _build_venue_lookups(VENUE_MAP_DATA)

    # ------------------------------------------------------------------
    # dump in the gametime stuff
    # ------------------------------------------------------------------
    gt_df = pd.read_csv(CSV_FILES["gametime"])
    gt_rows = []
    gt_parse_failures = 0

    for _, row in gt_df.iterrows():
        vis_id, home_id = _parse_event_name(row["name"], name_to_id)
        park_id = gt_to_park.get(row["venueId"])
        event_date = row["datetimeLocal"][:10] if pd.notna(row["datetimeLocal"]) else None

        if vis_id is None or home_id is None:
            gt_parse_failures += 1
            continue  # skip games if we can't figure out who is playing

        gt_rows.append((
            row["eventId"],
            row["name"],
            event_date,
            park_id,
            home_id,
            vis_id,
            int(row["minPriceTotal"]) if pd.notna(row["minPriceTotal"]) else None,
            int(row["maxPriceTotal"]) if pd.notna(row["maxPriceTotal"]) else None,
            float(row["trendingScore"]) if pd.notna(row["trendingScore"]) else None,
            row["venueId"],
        ))

    cur.executemany(
        "INSERT INTO gametime_events "
        "(event_id, event_name, event_date, park_id, home_team_id, vis_team_id, "
        " min_price, max_price, trending_score, source_venue_id) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        gt_rows,
    )
    print(f"  [OK] Loaded {len(gt_rows):,} Gametime events", end="")
    if gt_parse_failures:
        print(f"  ({gt_parse_failures} name-parse failures)")
    else:
        print()

    # ------------------------------------------------------------------
    # dump in the seatgeek stuff
    # ------------------------------------------------------------------
    sg_df = pd.read_csv(CSV_FILES["seatgeek"])
    sg_rows = []
    sg_parse_failures = 0

    for _, row in sg_df.iterrows():
        vis_id, home_id = _parse_event_name(row["name"], name_to_id)
        park_id = sg_to_park.get(row["venueId"])
        event_date = row["datetimeUtc"][:10] if pd.notna(row["datetimeUtc"]) else None

        if vis_id is None or home_id is None:
            sg_parse_failures += 1
            continue  # skip games if we can't figure out who is playing

        sg_rows.append((
            int(row["eventId"]),
            row["name"],
            event_date,
            park_id,
            home_id,
            vis_id,
            float(row["eventScore"]) if pd.notna(row["eventScore"]) else None,
            float(row["popularityScore"]) if pd.notna(row["popularityScore"]) else None,
            int(row["listingCount"]) if pd.notna(row["listingCount"]) else None,
            int(row["ticketCount"]) if pd.notna(row["ticketCount"]) else None,
            int(row["averagePrice"]) if pd.notna(row["averagePrice"]) else None,
            int(row["lowestPrice"]) if pd.notna(row["lowestPrice"]) else None,
            int(row["highestPrice"]) if pd.notna(row["highestPrice"]) else None,
            int(row["venueId"]),
        ))

    cur.executemany(
        "INSERT INTO seatgeek_events "
        "(event_id, event_name, event_date, park_id, home_team_id, vis_team_id, "
        " event_score, popularity_score, listing_count, ticket_count, "
        " avg_price, lowest_price, highest_price, source_venue_id) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        sg_rows,
    )
    print(f"  [OK] Loaded {len(sg_rows):,} SeatGeek events", end="")
    if sg_parse_failures:
        print(f"  ({sg_parse_failures} name-parse failures)")
    else:
        print()

    # ------------------------------------------------------------------
    # save everything and print a summary
    # ------------------------------------------------------------------
    conn.commit()

    all_tables = [
        "parks", "teams", "games",
        "team_lookup", "venue_map",
        "gametime_events", "seatgeek_events",
    ]
    print(f"\n  Database summary:")
    for table in all_tables:
        (count,) = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
        print(f"    {table:>20}: {count:>8,} rows")

    # quick check to see if the view works
    (view_count,) = cur.execute("SELECT COUNT(*) FROM v_ticket_pricing").fetchone()
    print(f"    {'v_ticket_pricing':>20}: {view_count:>8,} rows (view)")

    conn.close()
    print(f"\n  [OK] Database saved to {db_path}")


# ---------------------------------------------------------------------------
# main stuff
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
    print("  Baseball Attendance -- Database Builder")
    print(f"{'='*60}\n")
    build_database(db_path, force=args.force)
    print()


if __name__ == "__main__":
    main()
