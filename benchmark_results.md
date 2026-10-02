# Simulator Query Performance Benchmarks

This document contains the performance metrics for the SQL queries powering the Baseball Attendance Simulator. These tests were conducted by running each query 100 times to obtain an average execution time (these results were obtained on a Microsoft Surface Pro 11th Edition, 16gb ram).

These results are intended to be used for **Error Analysis** to demonstrate the impact of our composite indexes on database read performance.

## Results

| Query Type | Without Indexes (ms) | With Indexes (ms) | Performance Gain |
| :--- | :--- | :--- | :--- |
| **Matchup Prediction** | 1,104.59 | 297.14 | **~3.7x faster** |
| **Weather Impact** | 2,721.26 | 1,958.79 | **~1.4x faster** |
| **Day of Week Impact** | 2,650.00 | 1,972.89 | **~1.3x faster** |
| **Ticket Pricing Unified** | 5.61 | 3.19 | **~1.8x faster** |

## Indexes Tested

The following composite indexes were toggled to generate these benchmarks:

```sql
CREATE INDEX idx_games_team_dow ON games(home_team_id, day_of_week);
CREATE INDEX idx_games_team_daynight ON games(home_team_id, daynight);
CREATE INDEX idx_games_team_weather ON games(home_team_id, sky, precip);
CREATE INDEX idx_gt_team_matchup ON gametime_events(home_team_id, vis_team_id);
CREATE INDEX idx_sg_team_matchup ON seatgeek_events(home_team_id, vis_team_id);
```

## How to Reproduce

You can reproduce these results at any time by running the benchmark script in the repository:

```bash
python benchmark.py
```
