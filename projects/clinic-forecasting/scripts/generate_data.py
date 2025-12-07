import pandas as pd
import numpy as np
from pathlib import Path

# --- SETUP PATHS ---
# This ensures the file saves to the right place, no matter where you run the script from
script_dir = Path(__file__).parent
# Go up one level from 'scripts' to 'clinic-forecasting', then into 'data/raw'
output_dir = script_dir.parent / "data" / "raw"
output_dir.mkdir(parents=True, exist_ok=True) # Ensure folder exists

# 1. Setup Environment
np.random.seed(42)

# 2. Define Time Range
start_date = '2020-01-01'
end_date = '2025-12-31'
dates = pd.date_range(start=start_date, end=end_date, freq='D')
n_days = len(dates)

# 3. Create Base DataFrame
df = pd.DataFrame({'date': dates})
df['year'] = df['date'].dt.year
df['month'] = df['date'].dt.month
df['day_of_week'] = df['date'].dt.dayofweek

# --- COMPONENT 1: TREND ---
initial_visits = 35
total_growth = 1.03 ** 6
trend_factor = np.linspace(1.0, total_growth, n_days)

# --- COMPONENT 2: SEASONALITY ---
def get_seasonality(month):
    if month == 8: 
        return 1.25
    elif month == 12: 
        return 1.20
    elif month == 2: 
        return 0.85
    elif month in [6, 7]: 
        return 1.10
    else: 
        return 1.0

df['seasonal_factor'] = df['month'].apply(get_seasonality)

# --- COMPONENT 3: WEEKLY PATTERN ---
def get_weekly_pattern(day):
    if day == 6: 
        return 0.0       # Sunday
    elif day == 5: 
        return 0.3     # Saturday
    elif day == 4: 
        return 0.8     # Friday
    else: 
        return 1.0              # Mon-Thu

df['weekly_factor'] = df['day_of_week'].apply(get_weekly_pattern)

# --- COMPONENT 4: EXTERNAL SHOCK (COVID-19) ---
covid_mask = (df['date'] >= '2020-03-15') & (df['date'] <= '2020-05-31')
df['shock_factor'] = 1.0
df.loc[covid_mask, 'shock_factor'] = 0.15

# --- COMPONENT 5: NOISE ---
noise = np.random.normal(loc=0, scale=3, size=n_days)

# --- FINAL CALCULATION ---
df['visits'] = (initial_visits * trend_factor * df['seasonal_factor'] * df['weekly_factor'] * df['shock_factor']) + noise
df['visits'] = df['visits'].clip(lower=0).round().astype(int)

# 4. Save to CSV (Using the robust path)
file_path = output_dir / 'clinic_visits_2020_2025.csv'
df[['date', 'visits']].to_csv(file_path, index=False)

print(f"✅ Successfully generated data at: {file_path}")
print(f"Total Rows: {len(df)}")

# (Optional: Clean up the root file if you want to run this manually once)
# import os
# if os.path.exists("clinic_visits_2020_2025.csv"):
#     os.remove("clinic_visits_2020_2025.csv")