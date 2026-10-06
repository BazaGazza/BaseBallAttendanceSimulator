import os
import joblib
import pandas as pd

MODEL_PATH = "model.joblib"

def get_model():
    """Loads the pre-trained Scikit-Learn pipeline."""
    if not os.path.exists(MODEL_PATH):
        print(f"Error: '{MODEL_PATH}' not found. Run mockup.txt.rtf first to train and export the model.")
        exit(1)
    return joblib.load(MODEL_PATH)

def main():
    model = get_model()
    
    print("==============================================")
    print("      BASEBALL ATTENDANCE SIMULATOR (ML)      ")
    print("==============================================")
    
    # Collect scenario parameters from terminal user
    home = input("Home Team ID (e.g., BOS, NYA, LAN): ").strip().upper()
    vis = input("Visiting Team ID (e.g., NYA, BOS, CHN): ").strip().upper()
    dow = input("Day of Week (e.g., Saturday, Friday): ").strip().capitalize()
    daynight = input("Time of Day (day / night): ").strip().lower()
    sky = input("Sky Condition (sunny / cloudy / overcast / dome): ").strip().lower()
    precip = input("Precipitation (none / rain / drizzle): ").strip().lower()
    
    try:
        temp = float(input("Temperature (°F): ").strip())
    except ValueError:
        temp = 72.0  # Fallback median temperature
        
    # Format input payload
    input_df = pd.DataFrame([{
        "home_team_id": home,
        "vis_team_id": vis,
        "day_of_week": dow,
        "daynight": daynight,
        "sky": sky,
        "precip": precip,
        "temp": temp
    }])
    
    # Predict attendance
    predicted_fans = model.predict(input_df)
    
    print("\n----------------------------------------------")
    print(f" Predicted Attendance: {max(0, int(predicted_fans)):,} fans")
    print("----------------------------------------------\n")

if __name__ == "__main__":
    main()