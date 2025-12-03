import requests
import pandas as pd
from pathlib import Path
import os

# --- CONFIGURATION ---
# 1. Site Locations (Live Data)
SITES_URL = "https://data.hrsa.gov/DataDownload/DD_Files/Health_Center_Service_Delivery_and_LookAlike_Sites.xlsx"

# 2. Grantee Data (Direct FOIA Link found by You!)
# This is the 2024 H80 Awardee data.
UDS_URL = "https://www.hrsa.gov/sites/default/files/hrsa/foia/h80-2024.xlsx"

BASE_DIR = Path(__file__).parent.parent
RAW_DATA_DIR = BASE_DIR / "data" / "raw"

def download_file(url, filename):
    print(f"⬇️  Downloading: {filename}...")
    try:
        # Some govt servers require a User-Agent to prove we aren't a malicious bot
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
        
        response = requests.get(url, headers=headers, timeout=60)
        response.raise_for_status()
        
        output_path = RAW_DATA_DIR / filename
        with open(output_path, 'wb') as f:
            f.write(response.content)
        print(f"✅ Saved to: {output_path}")
        return True
    except Exception as e:
        print(f"❌ Error downloading {filename}: {e}")
        return False

def ingest_data():
    print("🚀 Starting Multi-Source Ingestion...")
    os.makedirs(RAW_DATA_DIR, exist_ok=True)
    
    # 1. Download Site Locations
    download_file(SITES_URL, "hrsa_sites.xlsx")
    
    # 2. Download UDS/Grantee Data
    if download_file(UDS_URL, "uds_2024.xlsx"):
        # Quick validation since we are using a new source
        try:
            print("🔎 Inspecting new UDS file...")
            df = pd.read_excel(RAW_DATA_DIR / "uds_2024.xlsx")
            print(f"   Rows: {len(df)}")
            print(f"   Columns: {list(df.columns[:5])}") # Print first 5 cols to verify
        except Exception as e:
            print(f"⚠️ File downloaded but could not be read: {e}")

if __name__ == "__main__":
    ingest_data()