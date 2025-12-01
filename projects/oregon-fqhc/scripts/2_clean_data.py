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
    
    # Clean column names (strip whitespace)
    df.columns = df.columns.str.strip()
    
    # Filter for Oregon
    state_col = 'Site State Abbreviation'
    if state_col not in df.columns:
        print(f"Column '{state_col}' not found.")
        return

    df_or = df[df[state_col] == 'OR'].copy()
    
    # --- NEW: Standardize Coordinates ---
    # Rename the awkward HRSA columns to simple 'latitude' and 'longitude'
    rename_map = {
        'Geocoding Artifact Address Primary Y Coordinate': 'latitude',
        'Geocoding Artifact Address Primary X Coordinate': 'longitude',
        'County Equivalent Name': 'county',
        'Site City': 'city',
        'Site Name': 'site_name',
        'Health Center Type': 'type'
    }
    
    # Rename only columns that exist
    df_or = df_or.rename(columns=rename_map)
    
    # Drop rows without coordinates (cannot map them)
    initial_count = len(df_or)
    df_or = df_or.dropna(subset=['latitude', 'longitude'])
    dropped_count = initial_count - len(df_or)
    
    if dropped_count > 0:
        print(f"Dropped {dropped_count} sites missing coordinates.")

    # Save
    df_or.to_csv(PROCESSED_DATA_PATH, index=False)
    
    print(f"Success! Processed data saved to: {PROCESSED_DATA_PATH}")
    print(f"Oregon Sites Mapped: {df_or.shape[0]}")

if __name__ == "__main__":
    clean_data()