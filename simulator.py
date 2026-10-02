import argparse
import sys
import pandas as pd
from queries import AttendanceAnalyzer

class GameSimulator:
    def __init__(self):
        self.qa = AttendanceAnalyzer()

    def simulate(
        self,
        home_team: str,
        vis_team: str,
        day_of_week: str,
        daynight: str,
        sky: str = None,
        precip: str = None,
        temp: int = None
    ):
        print(f"\n{'='*60}")
        print(f"  BASEBALL ATTENDANCE SIMULATOR")
        print(f"{'='*60}")
        print(f"  Matchup: {vis_team} at {home_team}")
        print(f"  Timing:  {day_of_week} ({daynight})")
        if sky and precip and temp is not None:
            print(f"  Weather: {sky}, {precip}, {temp}°F")
        print(f"{'-'*60}\n")

        # step 1: predict attendance using past games
        print("1. ATTENDANCE PREDICTION")
        print("------------------------")
        df_att = self.qa.simulate_attendance(home_team, vis_team, day_of_week, daynight)
        
        if df_att.empty or pd.isna(df_att.iloc[0]['predicted_attendance']):
            print("  [!] Insufficient historical data to make a prediction.")
        else:
            row = df_att.iloc[0]
            print(f"  Predicted Attendance: {int(row['predicted_attendance']):,}")
            print(f"  Expected Range:       {int(row['low_estimate']):,} to {int(row['high_estimate']):,}")
            print(f"  Confidence Basis:     {row['match_level']} (n={int(row['sample_size'])})")

        # step 2: show how much the weather and day of the week change the attendance
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
        print("\n3. SECONDARY TICKET MARKET PREDICTION")
        print("-------------------------------------")
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
    valid_dows = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    
    # loop forever until the user quits
    while True:
        try:
            home = input("\nHome Team ID (e.g. BOS): ").strip().upper()
            if not home: continue
            if home not in valid_teams:
                print(f"  [!] invalid home team. try one of these: {', '.join(valid_teams[:5])}...")
                continue
            
            vis = input("Visiting Team ID (e.g. NYA): ").strip().upper()
            if vis not in valid_teams:
                print(f"  [!] invalid visiting team. try one of these: {', '.join(valid_teams[:5])}...")
                continue
            
            if home == vis:
                print("  [!] a team can't play itself!")
                continue
                
            dow = input("Day of Week (e.g. Saturday): ").strip().title()
            if dow not in valid_dows:
                print("  [!] invalid day of week. try Monday, Tuesday, etc.")
                continue
                
            dn = input("Day or Night (day/night): ").strip().lower()
            if dn not in ['day', 'night']:
                print("  [!] invalid input. must be 'day' or 'night'.")
                continue
            
            # ask if they want to add weather info
            do_weather = input("Include weather factors? (y/n): ").strip().lower() == 'y'
            sky = None
            precip = None
            temp = None
            if do_weather:
                sky = input("Sky (e.g. sunny, cloudy, overcast): ").strip().lower()
                precip = input("Precipitation (e.g. none, rain, drizzle): ").strip().lower()
                temp_str = input("Temperature (F): ").strip()
                temp = int(temp_str) if temp_str.isdigit() else 70
                
            sim.simulate(home, vis, dow, dn, sky, precip, temp)
            
        except (KeyboardInterrupt, EOFError):
            print("\nExiting simulator.")
            sys.exit(0)
        except Exception as e:
            print(f"\nError during simulation: {e}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Baseball Attendance & Ticket Simulator")
    parser.add_argument("--home", type=str, help="Home team ID (e.g. BOS)")
    parser.add_argument("--vis", type=str, help="Visiting team ID (e.g. NYA)")
    parser.add_argument("--dow", type=str, help="Day of week (e.g. Saturday)")
    parser.add_argument("--dn", type=str, choices=['day', 'night'], help="Day or night game")
    parser.add_argument("--sky", type=str, help="Sky condition (e.g. sunny, cloudy)")
    parser.add_argument("--precip", type=str, help="Precipitation (e.g. none, rain)")
    parser.add_argument("--temp", type=int, help="Temperature in Fahrenheit")
    parser.add_argument("-i", "--interactive", action="store_true", help="Run in interactive mode")
    
    args = parser.parse_args()
    
    if args.interactive:
        interactive_mode()
    elif args.home and args.vis and args.dow and args.dn:
        sim = GameSimulator()
        sim.simulate(
            home_team=args.home.upper(),
            vis_team=args.vis.upper(),
            day_of_week=args.dow.title(),
            daynight=args.dn.lower(),
            sky=args.sky.lower() if args.sky else None,
            precip=args.precip.lower() if args.precip else None,
            temp=args.temp
        )
    else:
        parser.print_help()
        print("\nExample usage:")
        print("  python simulator.py --home BOS --vis NYA --dow Saturday --dn day --sky sunny --precip none --temp 75")
        print("  python simulator.py -i")
