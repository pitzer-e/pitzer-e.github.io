import pandas as pd
from pathlib import Path

# --- CONFIGURATION ---
BASE_DIR = Path(__file__).parent.parent
RAW_DATA_PATH = BASE_DIR / "data" / "raw" / "hrsa_data.xlsx"
PROCESSED_DATA_PATH = BASE_DIR / "data" / "processed" / "oregon_sites.csv"

def clean_data():
    print("Starting Data Cleaning Process...")

    if not RAW_DATA_PATH.exists():
        print(f"Error: Raw data not found at {RAW_DATA_PATH}")
        return

    df = pd.read_excel(RAW_DATA_PATH, engine='openpyxl')
    df.columns = df.columns.str.strip()
    
    # Filter for Oregon
    state_col = 'Site State Abbreviation'
    if state_col not in df.columns:
        print(f"Column '{state_col}' not found.")
        return

    df_or = df[df[state_col] == 'OR'].copy()
    
    # --- MAPPING COLUMNS ---
    # We are adding 'Health Center Name' -> 'organization'
    rename_map = {
        'Geocoding Artifact Address Primary Y Coordinate': 'latitude',
        'Geocoding Artifact Address Primary X Coordinate': 'longitude',
        'County Equivalent Name': 'county',
        'Site City': 'city',
        'Site Name': 'site_name',
        'Health Center Type': 'type',
        'Health Center Name': 'organization' # <--- NEW FIELD
    }
    
    # safe rename (only renames if column exists)
    # We check if 'Health Center Name' exists first to avoid errors if HRSA changed it
    if 'Health Center Name' not in df_or.columns:
        print("Warning: 'Health Center Name' column not found. Check raw data.")
    
    df_or = df_or.rename(columns=rename_map)
    
    # Keep only the columns we want (plus the new one)
    # This filters out the 50+ other columns we don't need
    target_cols = ['organization', 'site_name', 'city', 'county', 'type', 'latitude', 'longitude']
    
    # Only keep columns that actually exist in our dataframe
    existing_cols = [c for c in target_cols if c in df_or.columns]
    df_or = df_or[existing_cols]
    
    # Drop rows without coordinates
    df_or = df_or.dropna(subset=['latitude', 'longitude'])

    # Save
    df_or.to_csv(PROCESSED_DATA_PATH, index=False)
    print(f"Success! Processed data saved to: {PROCESSED_DATA_PATH}")
    print(f"   Columns: {list(df_or.columns)}")

if __name__ == "__main__":
    clean_data()