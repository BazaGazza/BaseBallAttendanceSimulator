"""
[PROTOTYPE] queries.py — Analytical SQL queries against the baseball attendance database.

Provides a library of reusable queries for exploring attendance patterns,
park factors, and environmental impacts. Each function connects to the DB,
runs a query, and returns a pandas DataFrame.

Usage:
    from queries import AttendanceAnalyzer
    qa = AttendanceAnalyzer()       # defaults to baseball_attendance.db
    qa.attendance_by_team()         # → DataFrame
"""

import os
import sqlite3

import pandas as pd

DB_NAME = "baseball_attendance.db"
DATA_DIR = os.path.dirname(os.path.abspath(__file__))


class AttendanceAnalyzer:
    """Run pre-built analytical queries against the baseball SQLite DB."""

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or os.path.join(DATA_DIR, DB_NAME)
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(
                f"Database not found: {self.db_path}\n"
                "Run `python db_setup.py` first."
            )

    def _query(self, sql: str, params: tuple = ()) -> pd.DataFrame:
        """Execute a query and return a DataFrame."""
        with sqlite3.connect(self.db_path) as conn:
            return pd.read_sql_query(sql, conn, params=params)

    # ------------------------------------------------------------------
    # 1. Attendance by team (all-time & season-level)
    # ------------------------------------------------------------------
    def attendance_by_team(self, season: int | None = None) -> pd.DataFrame:
        """Average and total attendance per home team, optionally for a season."""
        where = "WHERE g.gametype = 'regular'"
        params: tuple = ()
        if season:
            where += " AND g.season = ?"
            params = (season,)

        sql = f"""
        SELECT
            g.home_team_id                          AS team,
            g.season,
            COUNT(*)                                AS games,
            ROUND(AVG(g.attendance))                AS avg_attendance,
            SUM(g.attendance)                       AS total_attendance,
            MIN(g.attendance)                       AS min_attendance,
            MAX(g.attendance)                       AS max_attendance
        FROM games g
        {where}
          AND g.attendance IS NOT NULL
        GROUP BY g.home_team_id, g.season
        ORDER BY avg_attendance DESC
        """
        return self._query(sql, params)

    # ------------------------------------------------------------------
    # 2. Day-of-week attendance patterns
    # ------------------------------------------------------------------
    def attendance_by_day_of_week(self) -> pd.DataFrame:
        """Average attendance broken down by day of the week."""
        sql = """
        SELECT
            day_of_week,
            COUNT(*)                    AS games,
            ROUND(AVG(attendance))      AS avg_attendance,
            ROUND(AVG(total_runs), 2)   AS avg_runs
        FROM games
        WHERE gametype = 'regular'
          AND attendance IS NOT NULL
        GROUP BY day_of_week
        ORDER BY avg_attendance DESC
        """
        return self._query(sql)

    # ------------------------------------------------------------------
    # 3. Day vs Night attendance
    # ------------------------------------------------------------------
    def attendance_day_vs_night(self) -> pd.DataFrame:
        """Compare day-game vs night-game attendance."""
        sql = """
        SELECT
            daynight,
            COUNT(*)                    AS games,
            ROUND(AVG(attendance))      AS avg_attendance,
            ROUND(AVG(total_runs), 2)   AS avg_runs
        FROM games
        WHERE gametype = 'regular'
          AND attendance IS NOT NULL
          AND daynight IN ('day', 'night')
        GROUP BY daynight
        """
        return self._query(sql)

    # ------------------------------------------------------------------
    # 4. Weather impact on attendance
    # ------------------------------------------------------------------
    def attendance_by_weather(self) -> pd.DataFrame:
        """Average attendance grouped by sky condition and precipitation."""
        sql = """
        SELECT
            sky,
            precip,
            COUNT(*)                    AS games,
            ROUND(AVG(attendance))      AS avg_attendance,
            ROUND(AVG(temp), 1)         AS avg_temp
        FROM games
        WHERE gametype = 'regular'
          AND attendance IS NOT NULL
          AND sky IS NOT NULL
        GROUP BY sky, precip
        ORDER BY avg_attendance DESC
        """
        return self._query(sql)

    # ------------------------------------------------------------------
    # 5. Temperature bins and attendance
    # ------------------------------------------------------------------
    def attendance_by_temp_range(self) -> pd.DataFrame:
        """Bucket temperatures into ranges and show attendance patterns."""
        sql = """
        SELECT
            CASE
                WHEN temp < 50  THEN '< 50°F'
                WHEN temp < 60  THEN '50-59°F'
                WHEN temp < 70  THEN '60-69°F'
                WHEN temp < 80  THEN '70-79°F'
                WHEN temp < 90  THEN '80-89°F'
                ELSE '90°F+'
            END AS temp_range,
            COUNT(*)                    AS games,
            ROUND(AVG(attendance))      AS avg_attendance,
            ROUND(AVG(total_runs), 2)   AS avg_runs
        FROM games
        WHERE gametype = 'regular'
          AND attendance IS NOT NULL
          AND temp IS NOT NULL
          AND temp > 0
        GROUP BY temp_range
        ORDER BY MIN(temp)
        """
        return self._query(sql)

    # ------------------------------------------------------------------
    # 6. Park Run Factor (ballpark effects on scoring)
    # ------------------------------------------------------------------
    def park_run_factors(self, min_games: int = 50) -> pd.DataFrame:
        """
        Calculate a simple Run Park Factor per venue.

        Park Factor = (avg runs at park) / (league avg runs) * 100
        Values > 100 → hitter-friendly; < 100 → pitcher-friendly.
        """
        sql = f"""
        WITH league_avg AS (
            SELECT ROUND(AVG(total_runs), 4) AS lg_avg_runs
            FROM games
            WHERE gametype = 'regular'
              AND total_runs IS NOT NULL
        ),
        park_stats AS (
            SELECT
                g.park_id,
                p.park_name,
                p.city,
                p.state,
                COUNT(*)                       AS games,
                ROUND(AVG(g.total_runs), 4)    AS park_avg_runs
            FROM games g
            JOIN parks p ON g.park_id = p.park_id
            WHERE g.gametype = 'regular'
              AND g.total_runs IS NOT NULL
            GROUP BY g.park_id
            HAVING COUNT(*) >= ?
        )
        SELECT
            ps.park_id,
            ps.park_name,
            ps.city || ', ' || ps.state        AS location,
            ps.games,
            ps.park_avg_runs,
            la.lg_avg_runs,
            ROUND(ps.park_avg_runs / la.lg_avg_runs * 100, 1) AS run_factor
        FROM park_stats ps, league_avg la
        ORDER BY run_factor DESC
        """
        return self._query(sql, (min_games,))

    # ------------------------------------------------------------------
    # 7. Season-over-season attendance trend
    # ------------------------------------------------------------------
    def attendance_trend(self) -> pd.DataFrame:
        """League-wide average attendance per season."""
        sql = """
        SELECT
            season,
            COUNT(*)                    AS games,
            ROUND(AVG(attendance))      AS avg_attendance,
            SUM(attendance)             AS total_attendance
        FROM games
        WHERE gametype = 'regular'
          AND attendance IS NOT NULL
        GROUP BY season
        ORDER BY season
        """
        return self._query(sql)

    # ------------------------------------------------------------------
    # 8. Top rivalry matchups by attendance
    # ------------------------------------------------------------------
    def top_matchups(self, top_n: int = 20) -> pd.DataFrame:
        """Find the matchups (home vs visitor) that draw the biggest crowds."""
        sql = f"""
        SELECT
            home_team_id || ' vs ' || vis_team_id AS matchup,
            COUNT(*)                              AS games,
            ROUND(AVG(attendance))                AS avg_attendance,
            MAX(attendance)                       AS max_attendance
        FROM games
        WHERE gametype = 'regular'
          AND attendance IS NOT NULL
        GROUP BY home_team_id, vis_team_id
        HAVING COUNT(*) >= 10
        ORDER BY avg_attendance DESC
        LIMIT ?
        """
        return self._query(sql, (top_n,))


# ---------------------------------------------------------------------------
# Quick demo when run directly
# ---------------------------------------------------------------------------
def main():
    qa = AttendanceAnalyzer()

    sections = [
        ("League-Wide Attendance Trend (last 10 seasons)", lambda: qa.attendance_trend().tail(10)),
        ("Attendance by Day of Week", qa.attendance_by_day_of_week),
        ("Day vs Night Games", qa.attendance_day_vs_night),
        ("Attendance by Temperature Range", qa.attendance_by_temp_range),
        ("Top 10 Park Run Factors (min 50 games)", lambda: qa.park_run_factors().head(10)),
        ("Top 15 Rivalry Matchups by Avg Attendance", lambda: qa.top_matchups(15)),
    ]

    print(f"\n{'='*70}")
    print("  Baseball Attendance — Quick Analytics Report")
    print(f"{'='*70}")

    for title, query_fn in sections:
        print(f"\n{'-'*70}")
        print(f"  {title}")
        print(f"{'-'*70}")
        df = query_fn()
        print(df.to_string(index=False))

    print(f"\n{'='*70}\n")


if __name__ == "__main__":
    main()
