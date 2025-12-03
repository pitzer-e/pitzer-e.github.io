import pandas as pd
from pathlib import Path

# --- CONFIGURATION ---
BASE_DIR = Path(__file__).parent.parent
SITES_PATH = BASE_DIR / "data" / "processed" / "oregon_sites.csv"
UDS_PATH = BASE_DIR / "data" / "raw" / "uds_2024.xlsx"
FINAL_OUTPUT_PATH = BASE_DIR / "data" / "processed" / "oregon_sites_joined.csv"

def join_data():
    print("🔗 Starting Data Join (Spatial + Demographics)...")
    
    # 1. Load the Map Data (Sites)
    if not SITES_PATH.exists():
        print("❌ Processed sites file missing. Run 2_clean_data.py first.")
        return
    df_sites = pd.read_csv(SITES_PATH)
    # Ensure ID is a string to match UDS (remove .0 if it exists)
    df_sites['bhcmis_id'] = df_sites['bhcmis_id'].astype(str).str.replace(r'\.0$', '', regex=True)
    print(f"   Loaded {len(df_sites)} sites.")

    # 2. Load the Patient Data (UDS Table 4)
    if not UDS_PATH.exists():
        print("❌ UDS file missing. Run 1_ingest_data.py first.")
        return
    
    # Read Table4
    df_uds = pd.read_excel(UDS_PATH, sheet_name='Table4')
    
    # --- CRITICAL FIX: FORCE NUMERIC ---
    # Convert these columns to numbers. 
    # errors='coerce' turns any text (like footers/notes) into NaN (Not a Number)
    target_numeric_cols = ['T4_L6_Ca', 'T4_L7_Ca', 'T4_L7_Cb', 'T4_L8_Ca', 'T4_L8_Cb']
    
    for col in target_numeric_cols:
        # Check if column exists first (safety check)
        if col in df_uds.columns:
            df_uds[col] = pd.to_numeric(df_uds[col], errors='coerce')
        else:
            print(f"⚠️ Warning: Column {col} missing from UDS file.")

    # 3. Engineer the Metrics
    # Total Patients (Line 6)
    df_uds['total_patients'] = df_uds['T4_L6_Ca']
    
    # Uninsured (Line 7a + 7b)
    df_uds['uninsured'] = df_uds['T4_L7_Ca'] + df_uds['T4_L7_Cb']
    
    # Medicaid (Line 8a + 8b)
    df_uds['medicaid'] = df_uds['T4_L8_Ca'] + df_uds['T4_L8_Cb']
    
    # Calculate Percentages (Handle division by zero)
    df_uds['pct_uninsured'] = (df_uds['uninsured'] / df_uds['total_patients']).fillna(0)
    df_uds['pct_medicaid'] = (df_uds['medicaid'] / df_uds['total_patients']).fillna(0)
    
    # Prepare UDS for join
    cols_to_keep = ['BHCMISID', 'total_patients', 'uninsured', 'medicaid', 'pct_uninsured', 'pct_medicaid']
    df_uds_clean = df_uds[cols_to_keep].copy()
    
    # Standardize ID column for joining
    df_uds_clean['BHCMISID'] = df_uds_clean['BHCMISID'].astype(str).str.replace(r'\.0$', '', regex=True)
    df_uds_clean = df_uds_clean.rename(columns={'BHCMISID': 'bhcmis_id'})
    
    # Drop rows that don't have a valid ID (likely the footer rows we just coerced to NaN)
    df_uds_clean = df_uds_clean[df_uds_clean['bhcmis_id'] != 'nan']
    
    print(f"   Loaded UDS data for {len(df_uds_clean)} organizations.")

    # 4. Perform the Join
    df_merged = pd.merge(df_sites, df_uds_clean, on='bhcmis_id', how='left')
    
    # 5. Validation
    matched = df_merged['total_patients'].notnull().sum()
    print(f"   ✅ Matched patient data for {matched} out of {len(df_merged)} sites.")
    
    # Save
    df_merged.to_csv(FINAL_OUTPUT_PATH, index=False)
    print(f"✅ Success! Final dataset saved to: {FINAL_OUTPUT_PATH}")

if __name__ == "__main__":
    join_data()