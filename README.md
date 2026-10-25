# Baseball Attendance Simulator

Predict MLB game attendance and secondary-market ticket prices from 35 seasons of game logs, weather, and scheduling data.

The Baseball Attendance Simulator (BAS) combines historical Retrosheet game logs (1990–2025) with 2026 ticket listings from Gametime and SeatGeek in a single SQLite database. On top of that database it provides:

- **Attendance simulator (CLI):** predicts attendance for a hypothetical game, shows how the weekday and weather move the crowd, and estimates ticket prices for the matchup.
- **Analytics dashboard (Dash):** league-wide statistics and interactive charts.
- **Query benchmark:** measures how much the composite indexes speed up the simulator's queries.

Project website: [BazaGazza/BaseballWebsite](https://github.com/BazaGazza/BaseballWebsite)

## Quick start

Requires Python 3.10+.

```bash
git clone https://github.com/BazaGazza/BaseBallAttendanceSimulator.git
cd BaseBallAttendanceSimulator
pip install -r requirements.txt
python db_setup.py              # builds baseball_attendance.db from the CSVs
python simulator.py -i          # start the simulator
```

> **Windows:** if `python` can't find pandas, you may have more than one Python installed. Use the launcher with a version, e.g. `py -3.13 db_setup.py`.

## Usage

### Simulator

Interactive mode prompts for each value and keeps running until you press **Ctrl+C**:

```bash
python simulator.py -i
```

Or run a single prediction with arguments:

```bash
python simulator.py --home BOS --vis NYA --dow Saturday --dn day --sky sunny --precip none --temp 75
```

| Argument | Required | Values |
| :--- | :---: | :--- |
| `--home`, `--vis` | yes | Team code (see below) |
| `--dow` | yes | `Monday` … `Sunday` |
| `--dn` | yes | `day` or `night` |
| `--sky` | no | `sunny`, `cloudy`, `overcast`, `dome` |
| `--precip` | no | `none`, `drizzle`, `rain`, `showers`, `snow` |
| `--temp` | no | Temperature in °F |

The weather arguments are only used when all three are given.

Example output:

```
1. ATTENDANCE PREDICTION
  Predicted Attendance: 36,104
  Expected Range:       15,250 to 51,217
  Confidence Basis:     Exact Match (n=46)

2. FACTOR IMPACT ANALYSIS
  Day of Week (Friday)     : +2,461 fans

3. SECONDARY TICKET MARKET PREDICTION
  Predicted Floor Price:   $81.00
  Predicted Average Price: $200.00
  Predicted Ceiling Price: $2,207.00
  Data Source:             Exact Matchup (n=12)
```

**Confidence Basis** shows how the prediction was made. The simulator first averages past games with the same matchup, weekday, and day/night. If there are too few of those, it widens the search in steps: matchup + weekday, then matchup only, then the home team's overall average. `n` is the number of games used.

### Team codes

Codes follow Retrosheet, which marks the league in two-team cities (`NYA` Yankees / `NYN` Mets, `CHA` White Sox / `CHN` Cubs).

| Code | Team | Code | Team | Code | Team |
| :--- | :--- | :--- | :--- | :--- | :--- |
| ARI | Diamondbacks | HOU | Astros | PHI | Phillies |
| ATL | Braves | KCA | Royals | PIT | Pirates |
| BAL | Orioles | ANA | Angels | SDN | Padres |
| BOS | Red Sox | LAN | Dodgers | SFN | Giants |
| CHN | Cubs | MIA | Marlins | SEA | Mariners |
| CHA | White Sox | MIL | Brewers | SLN | Cardinals |
| CIN | Reds | MIN | Twins | TBA | Rays |
| CLE | Guardians | NYN | Mets | TEX | Rangers |
| COL | Rockies | NYA | Yankees | TOR | Blue Jays |
| DET | Tigers | ATH | Athletics | WAS | Nationals |

### Dashboard

```bash
pip install -r frontend/requirements.txt
cd frontend/src
python app.py
```

Then open http://localhost:8050. See [frontend/README.md](frontend/README.md) for adding pages and styling.

### Benchmark

```bash
python benchmark.py
```

Times four simulator queries with and without the composite indexes, then restores the indexes. Recorded results are in [benchmark_results.md](benchmark_results.md).

### Rebuilding the database

`db_setup.py` won't overwrite an existing database. To rebuild after changing the CSVs:

```bash
python db_setup.py --force
```

## How it works

```
clean_*.csv ──► db_setup.py ──► baseball_attendance.db ──► queries.py ──┬─► simulator.py
                                                                        ├─► frontend/ (Dash)
                                                                        └─► benchmark.py
```

- **`db_setup.py`** creates the schema, loads the CSVs, and links the ticket data to the game data. Ticket sites name games in text ("Pittsburgh Pirates at New York Mets"), so a regex and a team lookup table turn those names into team codes. A venue map does the same for stadium IDs. Gametime prices are stored in cents and converted to dollars.
- **`queries.py`** holds all the SQL in one class, `AttendanceAnalyzer`. Every method runs a parameterized query and returns a pandas DataFrame.
- **`simulator.py`**, the **dashboard**, and **`benchmark.py`** only call `queries.py` or the database; none of them build their own SQL from user input.

### Database

| Table | Rows | Contents |
| :--- | ---: | :--- |
| `games` | 84,430 | One row per game: date, park, teams, attendance, weather, score |
| `parks` | 672 | Every ballpark in the Retrosheet registry |
| `teams` | 36 | Team codes, including historical franchises |
| `team_lookup` | 30 | Full team name → team code |
| `venue_map` | 30 | Ticket-site venue IDs → park code |
| `gametime_events` | 2,437 | 2026 Gametime listings |
| `seatgeek_events` | 2,285 | 2026 SeatGeek listings |

Five views do the analysis: `v_ticket_pricing` (both ticket sources in one table), `v_team_attendance_stats`, `v_matchup_history`, `v_day_of_week_effects`, and `v_weather_impact`. Column definitions and data notes are in [DATA_GUIDE.md](DATA_GUIDE.md).

## Project structure

```
BaseBallAttendanceSimulator/
├── clean_*.csv            # Cleaned source data (games, parks, teams, gametime, seatgeek)
├── db_setup.py            # Builds baseball_attendance.db
├── queries.py             # AttendanceAnalyzer: all SQL queries
├── simulator.py           # Command-line simulator
├── benchmark.py           # Index performance benchmark
├── requirements.txt
├── frontend/              # Dash dashboard
│   ├── requirements.txt
│   └── src/
│       ├── app.py
│       ├── assets/        # CSS
│       ├── components/    # Stat and chart cards
│       └── pages/         # Dashboard pages
└── docs/
    └── technical_report/  # Technical report source (report.html) and screenshots
```

`baseball_attendance.db` is generated and not committed.

## Documentation

- [DATA_GUIDE.md](DATA_GUIDE.md): data dictionary, schema, and Retrosheet conventions
- [benchmark_results.md](benchmark_results.md): query performance with and without indexes
- [frontend/README.md](frontend/README.md): dashboard structure and how to add pages
- [docs/technical_report/](docs/technical_report/): full technical report (design, implementation, course concepts, user guide)

## Known limitations

- 2020 games played without fans are stored with attendance 0, which lowers team averages slightly.
- Night games are recorded with sky = `night`, so "sunny" weather only describes day games.
- Some games, mostly in domes, have a temperature of 0 and are counted as "Cold".
- Some Gametime listings report a maximum price of 0, which lowers the predicted ceiling price.

## Troubleshooting

| Problem | Fix |
| :--- | :--- |
| `No module named 'pandas'` or `'dash'` | Install the requirements for the Python you're running (`pip install -r requirements.txt`, plus `frontend/requirements.txt` for the dashboard). |
| `Database not found` | Run `python db_setup.py` from the project root. |
| `Database already exists` | Expected. Use `--force` only if you want to rebuild. |
| `invalid home team` | Use the Retrosheet code, e.g. `SDN` not `SD`. |
| `./run.sh` fails on Windows | It expects a Unix virtual environment. Use the dashboard commands above instead. |

## Team

CS 514 team project by:

- **Grant Trager:** data collection and cleaning, database design, queries, simulator, benchmark
- **Kyle Kline:** Dash dashboard
- **Rodolfo Baza Carrillo:** project website
- **Jimmy Ly:** website content, design support
