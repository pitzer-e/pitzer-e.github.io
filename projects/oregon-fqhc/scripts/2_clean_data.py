import pandas as pd
from pathlib import Path

# --- CONFIGURATION ---
# Define paths relative to this script
BASE_DIR = Path(__file__).parent.parent
RAW_DATA_PATH = BASE_DIR / "data" / "raw" / "hrsa_data.xlsx"
PROCESSED_DATA_PATH = BASE_DIR / "data" / "processed" / "oregon_sites.csv"

def clean_data():
    print("Starting Data Cleaning Process...")

    # 1. Load Raw Data
    if not RAW_DATA_PATH.exists():
        print(f"Error: Raw data not found at {RAW_DATA_PATH}")
        print("Run '1_ingest_data.py' first.")
        return

    df = pd.read_excel(RAW_DATA_PATH, engine='openpyxl')
    print(f"    Raw data loaded: {df.shape[0]} rows")

    # 2. Inspect Column Names (Crucial step when working with new data)
    # HRSA column names can be verbose. Let's standardize or find the State column.
    # We look for 'Site State Abbreviation' or similar.
    # To be safe, we strip whitespace from column names.
    df.columns = df.columns.str.strip()
    
    # Check if 'Site State Abbreviation' exists, if not try to find it
    state_col = 'Site State Abbreviation'
    if state_col not in df.columns:
        print(f"Column '{state_col}' not found. Available columns:")
        print(df.columns.tolist())
        return

    # 3. Filter for Oregon
    print("Filtering for Oregon (OR) sites...")
    df_or = df[df[state_col] == 'OR'].copy()

    # 4. Save Processed Data
    # index=False prevents pandas from writing the row numbers (0, 1, 2...) into the file
    df_or.to_csv(PROCESSED_DATA_PATH, index=False)
    
    print(f"Success! Processed data saved to: {PROCESSED_DATA_PATH}")
    print(f"Oregon Sites Found: {df_or.shape[0]}")

if __name__ == "__main__":
    clean_data()