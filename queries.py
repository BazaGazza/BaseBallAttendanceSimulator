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
        """get a list of all valid team ids"""
        df = self._query("SELECT team_id FROM teams")
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
    def simulate_attendance(
        self, home_team: str, vis_team: str, day_of_week: str, daynight: str
    ) -> pd.DataFrame:
        """find comparable games to predict attendance"""
        # start by looking for an exact match
        sql = """
        SELECT
            COUNT(*) AS sample_size,
            ROUND(AVG(attendance)) AS predicted_attendance,
            MIN(attendance) AS low_estimate,
            MAX(attendance) AS high_estimate,
            'Exact Match' AS match_level
        FROM games
        WHERE home_team_id = ? AND vis_team_id = ? 
          AND day_of_week = ? AND daynight = ?
          AND gametype = 'regular' AND attendance IS NOT NULL
        HAVING COUNT(*) >= 3
        """
        df = self._query(sql, (home_team, vis_team, day_of_week, daynight))
        if not df.empty: return df
        
        # if no exact match, drop the day/night filter and try again
        sql = """
        SELECT
            COUNT(*) AS sample_size,
            ROUND(AVG(attendance)) AS predicted_attendance,
            MIN(attendance) AS low_estimate,
            MAX(attendance) AS high_estimate,
            'Matchup + Day of Week' AS match_level
        FROM games
        WHERE home_team_id = ? AND vis_team_id = ? 
          AND day_of_week = ?
          AND gametype = 'regular' AND attendance IS NOT NULL
        HAVING COUNT(*) >= 3
        """
        df = self._query(sql, (home_team, vis_team, day_of_week))
        if not df.empty: return df

        # drop the day of week too
        sql = """
        SELECT
            COUNT(*) AS sample_size,
            ROUND(AVG(attendance)) AS predicted_attendance,
            MIN(attendance) AS low_estimate,
            MAX(attendance) AS high_estimate,
            'Matchup Only' AS match_level
        FROM games
        WHERE home_team_id = ? AND vis_team_id = ?
          AND gametype = 'regular' AND attendance IS NOT NULL
        HAVING COUNT(*) >= 5
        """
        df = self._query(sql, (home_team, vis_team))
        if not df.empty: return df

        # if all else fails, just use the home team's average
        sql = """
        SELECT
            COUNT(*) AS sample_size,
            ROUND(AVG(attendance)) AS predicted_attendance,
            MIN(attendance) AS low_estimate,
            MAX(attendance) AS high_estimate,
            'Team Baseline' AS match_level
        FROM games
        WHERE home_team_id = ?
          AND gametype = 'regular' AND attendance IS NOT NULL
        """
        return self._query(sql, (home_team,))

    def factor_impacts(self, home_team: str, day_of_week: str, sky: str = None, precip: str = None, temp: int = None) -> pd.DataFrame:
        """calculate how weather and day of the week change the attendance"""
        factors = []
        
        # figure out the day of the week impact
        sql_dow = "SELECT impact_vs_baseline FROM v_day_of_week_effects WHERE home_team_id = ? AND day_of_week = ?"
        df_dow = self._query(sql_dow, (home_team, day_of_week))
        if not df_dow.empty:
            factors.append({'Factor': f"Day of Week ({day_of_week})", 'Impact': df_dow.iloc[0]['impact_vs_baseline']})

        # figure out the weather impact (if they gave us weather info)
        if sky and precip and temp:
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
