"""Ballpark Attendance Linear Regression Model.

Loads clean Retrosheet game logs, trains an interpretable Scikit-Learn
pipeline, exports the serialized model artifact for deployment, and
prints coefficient impacts across teams, schedules, and weather.
"""

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


def load_and_preprocess(filepath: str = "clean_games.csv"):
  print(f"[1/5] Loading data from {filepath}...")
  df = pd.read_csv(filepath)

  # Target is attendance - rows without it cannot be used for training
  initial_count = len(df)
  df = df.dropna(subset=["attendance"])
  print(f"      Retained {len(df):,} of {initial_count:,} game records.")

  categorical_features = [
      "home_team_id",
      "vis_team_id",
      "day_of_week",
      "daynight",
      "sky",
      "precip",
  ]
  numeric_features = ["temp"]

  X = df[categorical_features + numeric_features]
  y = df["attendance"]

  return train_test_split(X, y, test_size=0.2, random_state=42)


def build_pipeline():
  print("[2/5] Building feature transformation and regression pipeline...")
  categorical_features = [
      "home_team_id",
      "vis_team_id",
      "day_of_week",
      "daynight",
      "sky",
      "precip",
  ]
  numeric_features = ["temp"]

  # Impute missing temperatures with median; no scaler so coefficients stay in degrees F
  numeric_transformer = Pipeline(
      steps=[("imputer", SimpleImputer(strategy="median"))]
  )

  # Handle missing categories and encode; drop='first' avoids dummy variable collinearity
  categorical_transformer = Pipeline(
      steps=[
          ("imputer", SimpleImputer(strategy="constant", fill_value="unknown")),
          (
              "onehot",
              OneHotEncoder(
                  handle_unknown="infrequent_if_exist",
                  min_frequency=10,
                  sparse_output=False,
              ),
          ),
      ]
  )

  preprocessor = ColumnTransformer(
      transformers=[
          ("num", numeric_transformer, numeric_features),
          ("cat", categorical_transformer, categorical_features),
      ]
  )

  return Pipeline(
      steps=[("preprocessor", preprocessor), ("regressor", LinearRegression())]
  )


def evaluate_model(model, X_test, y_test):
  print("[3/5] Evaluating performance on held-out test set...")
  preds = model.predict(X_test)
  mae = mean_absolute_error(y_test, preds)
  rmse = np.sqrt(mean_squared_error(y_test, preds))
  r2 = r2_score(y_test, preds)

  print(f"      Mean Absolute Error (MAE): {mae:,.0f} fans")
  print(f"      Root Mean Squared Error (RMSE): {rmse:,.0f} fans")
  print(f"      R-squared (R²): {r2:.3f}\n")


def export_and_inspect_coefficients(model, output_model_path="model.joblib"):
  print("[4/5] Serializing model artifact...")
  joblib.dump(model, output_model_path)
  print(f"      Saved model to: {output_model_path}\n")

  print("[5/5] Extracting factor impact coefficients...")
  preprocessor = model.named_steps["preprocessor"]
  regressor = model.named_steps["regressor"]

  # Retrieve all generated feature names
  raw_feature_names = preprocessor.get_feature_names_out()
  clean_feature_names = [
      col.replace("cat__", "").replace("num__", "") for col in raw_feature_names
  ]

  coef_df = pd.DataFrame({
      "factor": clean_feature_names,
      "attendance_impact": regressor.coef_,
  })

  print(f"Baseline Attendance (Intercept): {regressor.intercept_:,.0f} fans\n")

  # 1. Day of Week Breakdown
  dow = (
      coef_df[coef_df["factor"].str.startswith("day_of_week_")]
      .sort_values(by="attendance_impact", ascending=False)
      .reset_index(drop=True)
  )
  print("--- Day of Week Impact ---")
  print(dow.to_string(index=False))
  print()

  # 2. Top 5 Visiting Team Draws
  top_vis = (
      coef_df[coef_df["factor"].str.startswith("vis_team_id_")]
      .sort_values(by="attendance_impact", ascending=False)
      .head(5)
      .reset_index(drop=True)
  )
  print("--- Top 5 Visiting Opponent Draws ---")
  print(top_vis.to_string(index=False))
  print()

  # 3. Weather Conditions & Temperature
  weather = (
      coef_df[
          coef_df["factor"].str.startswith(("precip_", "sky_", "temp"))
      ].sort_values(by="attendance_impact", ascending=False)
  ).reset_index(drop=True)
  print("--- Weather & Temperature Impact ---")
  print(weather.to_string(index=False))
  print()


def run_single_inference_example(model):
  """Demonstrates how to predict attendance on an upcoming game."""
  sample_game = pd.DataFrame([{
      "home_team_id": "BOS",
      "vis_team_id": "NYA",
      "day_of_week": "Saturday",
      "daynight": "day",
      "sky": "sunny",
      "precip": "none",
      "temp": 72,
  }])

  pred = model.predict(sample_game)[0]
  print("--- Example Prediction ---")
  print(
      f"Matchup: NYA @ BOS (Saturday Day Game, 72°F, Sunny) -> Predicted"
      f" Attendance: {pred:,.0f} fans"
  )


if __name__ == "__main__":
  X_train, X_test, y_train, y_test = load_and_preprocess("clean_games.csv")

  model_pipeline = build_pipeline()
  model_pipeline.fit(X_train, y_train)

  evaluate_model(model_pipeline, X_test, y_test)
  export_and_inspect_coefficients(model_pipeline, "model.joblib")
  run_single_inference_example(model_pipeline)