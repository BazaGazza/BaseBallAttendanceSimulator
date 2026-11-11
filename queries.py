"""
queries.py - sql queries for the baseball database

this file has all the queries we need to figure out attendance patterns.
it connects to the db and gives back pandas dataframes.

how to use it:
    from queries import AttendanceAnalyzer
    qa = AttendanceAnalyzer()       # uses baseball_attendance.db
    qa.attendance_by_team()
"""

import os
import sqlite3

import pandas as pd

DB_NAME = "baseball_attendance.db"
DATA_DIR = os.path.dirname(os.path.abspath(__file__))


class AttendanceAnalyzer:
    """run queries against the baseball db"""

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or os.path.join(DATA_DIR, DB_NAME)
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(
                f"Database not found: {self.db_path}\n"
                "Run `python db_setup.py` first."
            )

    def _query(self, sql: str, params: tuple = ()) -> pd.DataFrame:
        """run a query and get a dataframe back"""
        with sqlite3.connect(self.db_path) as conn:
            return pd.read_sql_query(sql, conn, params=params)

    def get_valid_teams(self) -> list:
        """get a list of all 30 current MLB team ids"""
        df = self._query("SELECT team_id FROM team_lookup ORDER BY team_id")
        return df['team_id'].tolist()

    # ------------------------------------------------------------------
    # 1. attendance by team 
    # ------------------------------------------------------------------
    def attendance_by_team(self, season: int | None = None) -> pd.DataFrame:
        """get average and total attendance for each home team"""
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
    # 2. attendance based on the day of the week
    # ------------------------------------------------------------------
    def attendance_by_day_of_week(self) -> pd.DataFrame:
        """see how attendance changes depending on the day of the week"""
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
    # 3. day games vs night games
    # ------------------------------------------------------------------
    def attendance_day_vs_night(self) -> pd.DataFrame:
        """compare attendance for day and night games"""
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
    # 4. weather impact
    # ------------------------------------------------------------------
    def attendance_by_weather(self) -> pd.DataFrame:
        """see how weather affects the attendance"""
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
    # 5. temperature and attendance
    # ------------------------------------------------------------------
    def attendance_by_temp_range(self) -> pd.DataFrame:
        """group temperatures to see if it changes attendance"""
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
    # 6. park run factor
    # ------------------------------------------------------------------
    def park_run_factors(self, min_games: int = 50) -> pd.DataFrame:
        """
        calculate a simple run park factor for each stadium.

        park factor = (avg runs at park) / (league avg runs) * 100
        > 100 means hitter friendly, < 100 means pitcher friendly
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
    # 7. season over season attendance trend
    # ------------------------------------------------------------------
    def attendance_trend(self) -> pd.DataFrame:
        """get average attendance across the whole league per season"""
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
    # 8. top rivalry matchups
    # ------------------------------------------------------------------
    def top_matchups(self, top_n: int = 20) -> pd.DataFrame:
        """find out which matchups get the biggest crowds"""
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

    # ------------------------------------------------------------------
    # simulator queries
    # ------------------------------------------------------------------
    # postseason game types stored in the DB
    POSTSEASON_TYPES = ("divisionseries", "lcs", "worldseries", "wildcard", "playoff")

    def _run_sim_fallback(self, steps: list[tuple[str, tuple, str, int]]) -> pd.DataFrame:
        """Execute ordered simulation fallback queries and return the first hit."""
        for where_clause, params, label, min_count in steps:
            having = f"HAVING COUNT(*) >= {min_count}" if min_count > 0 else ""
            sql = f"""
            SELECT
                COUNT(*) AS sample_size,
                ROUND(AVG(attendance)) AS predicted_attendance,
                MIN(attendance) AS low_estimate,
                MAX(attendance) AS high_estimate,
                ? AS match_level
            FROM games
            WHERE {where_clause}
              AND attendance IS NOT NULL
              AND attendance > 0
              AND season != 2020
            {having}
            """
            df = self._query(sql, (label, *params))
            if not df.empty and pd.notna(df.iloc[0]["predicted_attendance"]):
                return df
        return pd.DataFrame()

    def simulate_attendance(
        self, home_team: str, vis_team: str, day_of_week: str, daynight: str,
        game_type: str = "regular"
    ) -> pd.DataFrame:
        """find comparable games to predict attendance, scoped to the current park
        and capped at stadium seating capacity.

        game_type: 'regular' or 'postseason'
        """
        park_id = self.get_park_id(home_team)
        capacity = self.get_park_capacity(park_id) if park_id else None

        if game_type == "postseason":
            df = self._simulate_postseason(home_team, vis_team, park_id)
        else:
            df = self._simulate_regular(home_team, vis_team, day_of_week, daynight, park_id)

        if capacity is not None and not df.empty and pd.notna(df.iloc[0]["predicted_attendance"]):
            for col in ("predicted_attendance", "low_estimate", "high_estimate"):
                df[col] = df[col].clip(upper=capacity)

        return df

    def _simulate_regular(
        self, home_team: str, vis_team: str, day_of_week: str, daynight: str,
        park_id: str | None = None
    ) -> pd.DataFrame:
        """fallback chain for regular-season attendance prediction."""
        base = "gametype = 'regular'"
        steps = []
        if park_id:
            steps.extend([
                (f"{base} AND park_id = ? AND home_team_id = ? AND vis_team_id = ? AND day_of_week = ? AND daynight = ?",
                 (park_id, home_team, vis_team, day_of_week, daynight), "Exact Match", 3),
                (f"{base} AND park_id = ? AND home_team_id = ? AND vis_team_id = ? AND day_of_week = ?",
                 (park_id, home_team, vis_team, day_of_week), "Matchup + Day of Week", 3),
                (f"{base} AND park_id = ? AND home_team_id = ? AND vis_team_id = ?",
                 (park_id, home_team, vis_team), "Matchup Only", 3),
                (f"{base} AND park_id = ? AND home_team_id = ?",
                 (park_id, home_team), "Team Baseline (Current Park)", 5),
            ])
        steps.append((f"{base} AND home_team_id = ?", (home_team,), "Team Baseline", 0))
        return self._run_sim_fallback(steps)

    def _simulate_postseason(
        self, home_team: str, vis_team: str, park_id: str | None = None
    ) -> pd.DataFrame:
        """fallback chain for postseason attendance prediction."""
        ps_filter = "gametype IN ('divisionseries','lcs','worldseries','wildcard','playoff')"
        steps = []
        if park_id:
            steps.extend([
                (f"{ps_filter} AND park_id = ? AND home_team_id = ? AND vis_team_id = ?",
                 (park_id, home_team, vis_team), "Postseason – Exact Matchup", 2),
                (f"{ps_filter} AND park_id = ? AND home_team_id = ?",
                 (park_id, home_team), "Postseason – Home Team", 2),
            ])
        steps.extend([
            (f"{ps_filter} AND home_team_id = ?",
             (home_team,), "Postseason – Home Team (All Parks)", 2),
            (ps_filter, (), "Postseason – League Average", 0),
        ])
        return self._run_sim_fallback(steps)

    def factor_impacts(self, home_team: str, day_of_week: str, sky: str = None, precip: str = None, temp: int = None) -> pd.DataFrame:
        """calculate how weather and day of the week change the attendance"""
        factors = []
        
        # figure out the day of the week impact
        sql_dow = "SELECT impact_vs_baseline FROM v_day_of_week_effects WHERE home_team_id = ? AND day_of_week = ?"
        df_dow = self._query(sql_dow, (home_team, day_of_week))
        if not df_dow.empty:
            factors.append({'Factor': f"Day of Week ({day_of_week})", 'Impact': df_dow.iloc[0]['impact_vs_baseline']})

        # figure out the weather impact (if they gave us weather info)
        if sky and precip and temp is not None:
            temp_bucket = 'Cold' if temp < 60 else ('Moderate' if temp <= 85 else 'Hot')
            sql_weather = "SELECT impact_vs_baseline FROM v_weather_impact WHERE home_team_id = ? AND sky = ? AND precip = ? AND temp_bucket = ?"
            df_weather = self._query(sql_weather, (home_team, sky, precip, temp_bucket))
            if not df_weather.empty:
                factors.append({'Factor': f"Weather ({sky}, {precip}, {temp_bucket})", 'Impact': df_weather.iloc[0]['impact_vs_baseline']})
                
        return pd.DataFrame(factors)

    def predict_ticket_prices(self, home_team: str, vis_team: str) -> pd.DataFrame:
        """predict ticket prices using our pricing view"""
        # try to find this exact matchup in our ticket data
        sql = """
        SELECT
            ROUND(AVG(floor_price)) AS predicted_floor,
            ROUND(AVG(ceiling_price)) AS predicted_ceiling,
            ROUND(AVG(avg_price)) AS predicted_avg,
            COUNT(*) AS data_points,
            'Exact Matchup' AS match_level
        FROM v_ticket_pricing
        WHERE home_team_id = ? AND vis_team_id = ?
        HAVING COUNT(*) > 0
        """
        df = self._query(sql, (home_team, vis_team))
        if not df.empty and pd.notna(df.iloc[0]['predicted_floor']):
            return df
            
        # if we can't find the exact matchup, just use the home team's average price
        sql = """
        SELECT
            ROUND(AVG(floor_price)) AS predicted_floor,
            ROUND(AVG(ceiling_price)) AS predicted_ceiling,
            ROUND(AVG(avg_price)) AS predicted_avg,
            COUNT(*) AS data_points,
            'Team Average' AS match_level
        FROM v_ticket_pricing
        WHERE home_team_id = ?
        """
        return self._query(sql, (home_team,))

    def get_park_capacity(
        self, park_id: str | None = None, home_team: str | None = None
    ) -> int | None:
        """Look up seating capacity by park_id or home_team_id."""
        if park_id:
            df = self._query(
                "SELECT seating_capacity FROM park_capacity WHERE park_id = ?",
                (park_id,),
            )
            if not df.empty:
                return int(df.iloc[0]["seating_capacity"])

        if home_team:
            # Find the primary/most recent park for this home team that has capacity data
            sql = """
            SELECT pc.seating_capacity
            FROM games g
            JOIN park_capacity pc ON g.park_id = pc.park_id
            WHERE g.home_team_id = ?
            ORDER BY g.game_date DESC
            LIMIT 1
            """
            df = self._query(sql, (home_team,))
            if not df.empty:
                return int(df.iloc[0]["seating_capacity"])
        return None

    def get_park_id(self, home_team: str) -> str | None:
        """Get the primary park_id for a given home_team_id."""
        sql = """
        SELECT park_id
        FROM games
        WHERE home_team_id = ? AND park_id IS NOT NULL
        GROUP BY park_id
        ORDER BY MAX(season) DESC, COUNT(*) DESC
        LIMIT 1
        """
        df = self._query(sql, (home_team,))
        if not df.empty:
            return str(df.iloc[0]["park_id"])
        return None

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
