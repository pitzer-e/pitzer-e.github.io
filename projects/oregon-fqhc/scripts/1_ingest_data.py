import requests
import pandas as pd
from pathlib import Path
import os

# --- CONFIGURATION ---
DATA_URL = "https://data.hrsa.gov/DataDownload/DD_Files/Health_Center_Service_Delivery_and_LookAlike_Sites.xlsx"

# Setup Paths relative to this script
# We want to go up one level (..) to 'oregon-fqhc', then into 'data/raw'
BASE_DIR = Path(__file__).parent.parent
RAW_DATA_DIR = BASE_DIR / "data" / "raw"
OUTPUT_FILE = RAW_DATA_DIR / "hrsa_data.xlsx"

def ingest_data():
    print(f"Starting Ingestion from: {DATA_URL}")
    
    # Ensure directory exists
    os.makedirs(RAW_DATA_DIR, exist_ok=True)
    
    # 1. Download the file
    try:
        response = requests.get(DATA_URL, timeout=30)
        response.raise_for_status() # Check for HTTP errors
        
        with open(OUTPUT_FILE, 'wb') as f:
            f.write(response.content)
        print(f"File downloaded successfully to: {OUTPUT_FILE}")
        
    except Exception as e:
        print(f"Error downloading file: {e}")
        return

    # 2. Quick Validation (Peek at the data)
    try:
        print("Validating file integrity...")
        # Reading specifically the 'health_center_service_delivery_sites' usually usually the main sheet
        # We will read without specifying sheet first to see what we get
        df = pd.read_excel(OUTPUT_FILE, engine='openpyxl') 
        
        print("Data Loaded Successfully!")
        print(f"   Rows: {df.shape[0]}")
        print(f"   Columns: {df.shape[1]}")
        print(f"   Columns Preview: {list(df.columns[:5])}")
        
    except Exception as e:
        print(f"Error reading the Excel file: {e}")

if __name__ == "__main__":
    ingest_data()