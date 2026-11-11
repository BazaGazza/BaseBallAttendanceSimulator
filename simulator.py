import argparse
import sys
import pandas as pd
from queries import AttendanceAnalyzer

class GameSimulator:
    VALID_DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")

    def __init__(self):
        self.qa = AttendanceAnalyzer()

    def simulate(
        self,
        home_team: str,
        vis_team: str,
        day_of_week: str = "Saturday",
        daynight: str = "night",
        sky: str = None,
        precip: str = None,
        temp: int = None,
        game_type: str = "regular"
    ):
        home_team = home_team.strip().upper()
        vis_team = vis_team.strip().upper()
        game_type = game_type.strip().lower()
        is_postseason = game_type == "postseason"

        valid_teams = self.qa.get_valid_teams()
        if home_team not in valid_teams:
            raise ValueError(f"Invalid home team '{home_team}'. Valid MLB teams: {', '.join(valid_teams)}")
        if vis_team not in valid_teams:
            raise ValueError(f"Invalid visiting team '{vis_team}'. Valid MLB teams: {', '.join(valid_teams)}")
        if home_team == vis_team:
            raise ValueError(f"Home and visiting team cannot be the same ('{home_team}').")

        print(f"\n{'='*60}")
        print(f"  BASEBALL ATTENDANCE SIMULATOR")
        print(f"{'='*60}")
        print(f"  Matchup:   {vis_team} at {home_team}")
        print(f"  Game Type: {'Post-Season' if is_postseason else 'Regular Season'}")
        if not is_postseason:
            print(f"  Timing:    {day_of_week} ({daynight})")
        if sky and precip and temp is not None:
            print(f"  Weather:   {sky}, {precip}, {temp}°F")
        print(f"{'-'*60}\n")

        # step 1: predict attendance using past games
        print("1. ATTENDANCE PREDICTION")
        print("------------------------")
        df_att = self.qa.simulate_attendance(home_team, vis_team, day_of_week, daynight,
                                             game_type=game_type)

        park_id = self.qa.get_park_id(home_team)
        capacity = self.qa.get_park_capacity(park_id) if park_id else None

        if df_att.empty or pd.isna(df_att.iloc[0]['predicted_attendance']):
            print("  [!] Insufficient historical data to make a prediction.")
        else:
            row = df_att.iloc[0]
            pred_att = int(row['predicted_attendance'])
            low_att = int(row['low_estimate'])
            high_att = int(row['high_estimate'])

            if capacity:
                pred_att = min(pred_att, capacity)
                low_att = min(low_att, capacity)
                high_att = min(high_att, capacity)

            print(f"  Predicted Attendance: {pred_att:,}")
            print(f"  Expected Range:       {low_att:,} to {high_att:,}")

            if capacity:
                pct_full = min(100.0, (pred_att / capacity) * 100)
                print(f"  Stadium Capacity:     {pct_full:.1f}% full ({pred_att:,} / {capacity:,})")

            print(f"  Confidence Basis:     {row['match_level']} (n={int(row['sample_size'])})")

        # step 2: show how much the weather and day of the week change the attendance
        # (skipped for postseason — sample sizes are too small to isolate factors)
        if not is_postseason:
            print("\n2. FACTOR IMPACT ANALYSIS")
            print("-------------------------")
            df_factors = self.qa.factor_impacts(home_team, day_of_week, sky, precip, temp)
            if df_factors.empty:
                print("  [!] Not enough data to isolate factor impacts.")
            else:
                for _, r in df_factors.iterrows():
                    impact = int(r['Impact'])
                    sign = "+" if impact > 0 else ""
                    print(f"  {r['Factor']:<25}: {sign}{impact:,} fans")

        # step 3: look up the ticket prices for this game
        # postseason ticket data is not available in our dataset — the secondary
        # market sources (SeatGeek/Gametime) only captured regular-season games,
        # so a postseason projection would be misleading. skip the section and
        # tell the user why.
        print("\n3. SECONDARY TICKET MARKET PREDICTION")
        print("-------------------------------------")
        if is_postseason:
            print("  [!] Postseason ticket pricing is not available.")
            print("      Our SeatGeek and Gametime datasets only cover regular-season")
            print("      games, so we don't have enough postseason secondary-market")
            print("      data to make a reliable price prediction.")
        else:
            df_tickets = self.qa.predict_ticket_prices(home_team, vis_team)
            if df_tickets.empty or pd.isna(df_tickets.iloc[0]['predicted_floor']):
                print("  [!] No secondary market data available for this matchup/team.")
            else:
                row = df_tickets.iloc[0]
                print(f"  Predicted Floor Price:   ${row['predicted_floor']:,.2f}")
                print(f"  Predicted Average Price: ${row['predicted_avg']:,.2f}" if pd.notna(row['predicted_avg']) else "  Predicted Average Price: N/A")
                print(f"  Predicted Ceiling Price: ${row['predicted_ceiling']:,.2f}")
                print(f"  Data Source:             {row['match_level']} (n={int(row['data_points'])})")

        print(f"\n{'='*60}\n")

def interactive_mode():
    print("Entering Interactive Simulator Mode.")
    print("Press Ctrl+C to exit at any time.\n")
    sim = GameSimulator()
    valid_teams = sim.qa.get_valid_teams()
    valid_dows = GameSimulator.VALID_DAYS
    
    # loop forever until the user quits
    while True:
        try:
            home = input("\nHome Team ID (e.g. BOS): ").strip().upper()
            if not home: continue
            if home not in valid_teams:
                print(f"  [!] '{home}' is not a current MLB team. Valid teams: {', '.join(valid_teams)}")
                continue
            
            vis = input("Visiting Team ID (e.g. NYA): ").strip().upper()
            if vis not in valid_teams:
                print(f"  [!] '{vis}' is not a current MLB team. Valid teams: {', '.join(valid_teams)}")
                continue
            
            if home == vis:
                print("  [!] a team can't play itself!")
                continue

            gt_input = input("Game type — regular or postseason? (r/p) [default: r]: ").strip().lower()
            if gt_input in ("", "r", "reg", "regular"):
                game_type = "regular"
            elif gt_input in ("p", "post", "postseason"):
                game_type = "postseason"
            else:
                print("  [!] invalid game type. enter 'r' (regular) or 'p' (postseason).")
                continue

            # day/time only needed for regular season
            dow = "Saturday"
            dn = "night"
            if game_type == "regular":
                dow = input("Day of Week (e.g. Saturday): ").strip().title()
                if dow not in valid_dows:
                    print("  [!] invalid day of week. try Monday, Tuesday, etc.")
                    continue
                    
                dn = input("Day or Night (day/night): ").strip().lower()
                if dn not in ['day', 'night']:
                    print("  [!] invalid input. must be 'day' or 'night'.")
                    continue
            
            # ask if they want to add weather info
            sky = None
            precip = None
            temp = None
            if game_type == "regular":
                do_weather = input("Include weather factors? (y/n): ").strip().lower() == 'y'
                if do_weather:
                    sky = input("Sky (e.g. sunny, cloudy, overcast): ").strip().lower()
                    precip = input("Precipitation (e.g. none, rain, drizzle): ").strip().lower()
                    temp_str = input("Temperature (F): ").strip()
                    try:
                        temp = int(temp_str)
                    except ValueError:
                        temp = 70
                
            sim.simulate(home, vis, dow, dn, sky, precip, temp, game_type=game_type)
            
        except (KeyboardInterrupt, EOFError):
            print("\nExiting simulator.")
            sys.exit(0)
        except Exception as e:
            print(f"\nError during simulation: {e}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Baseball Attendance & Ticket Simulator")
    parser.add_argument("--home", type=str, help="Home team ID (e.g. BOS)")
    parser.add_argument("--vis", type=str, help="Visiting team ID (e.g. NYA)")
    parser.add_argument("--dow", type=str, help="Day of week (e.g. Saturday) — regular season only")
    parser.add_argument("--dn", type=str, choices=['day', 'night'], help="Day or night game — regular season only")
    parser.add_argument("--sky", type=str, help="Sky condition (e.g. sunny, cloudy) — regular season only")
    parser.add_argument("--precip", type=str, help="Precipitation (e.g. none, rain) — regular season only")
    parser.add_argument("--temp", type=int, help="Temperature in Fahrenheit — regular season only")
    parser.add_argument(
        "--gametype", type=str, choices=["regular", "postseason"], default="regular",
        help="Game type: 'regular' (default) or 'postseason'"
    )
    parser.add_argument("-i", "--interactive", action="store_true", help="Run in interactive mode")
    
    args = parser.parse_args()
    
    if args.interactive:
        interactive_mode()
    elif args.home and args.vis:
        is_postseason = args.gametype == "postseason"
        # for postseason, dow/dn aren't required
        if not is_postseason:
            if not (args.dow and args.dn):
                parser.error("--dow and --dn are required for regular season games")
            if args.dow.title() not in GameSimulator.VALID_DAYS:
                parser.error(f"Invalid --dow '{args.dow}'. Must be one of: {', '.join(GameSimulator.VALID_DAYS)}")
        sim = GameSimulator()
        try:
            sim.simulate(
                home_team=args.home.upper(),
                vis_team=args.vis.upper(),
                day_of_week=args.dow.title() if args.dow else "Saturday",
                daynight=args.dn.lower() if args.dn else "night",
                sky=args.sky.lower() if args.sky else None,
                precip=args.precip.lower() if args.precip else None,
                temp=args.temp,
                game_type=args.gametype,
            )
        except ValueError as e:
            parser.error(str(e))
    else:
        parser.print_help()
        print("\nExample usage (regular season):")
        print("  python simulator.py --home BOS --vis NYA --dow Saturday --dn day --sky sunny --precip none --temp 75")
        print("\nExample usage (postseason):")
        print("  python simulator.py --home BOS --vis NYA --gametype postseason")
        print("  python simulator.py -i")
