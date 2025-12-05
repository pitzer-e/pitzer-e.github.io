import pandas as pd
from pathlib import Path

# --- CONFIGURATION ---
BASE_DIR = Path(__file__).parent.parent
DATA_PATH = BASE_DIR / "data" / "processed" / "oregon_sites_joined.csv"

def analyze_data():
    print("Starting Correlation Analysis...")
    
    if not DATA_PATH.exists():
        print("Data file missing.")
        return

    df = pd.read_csv(DATA_PATH)
    
    # 1. Clean Data for Analysis
    # We filter out tiny clinics (e.g., < 100 patients) to avoid skewing the trend
    df_analysis = df[df['total_patients'] > 100].copy()
    
    # 2. Calculate Correlation
    # Do larger clinics serve a higher % of Medicaid patients?
    # We verify the columns exist to satisfy strict linters
    if 'total_patients' in df_analysis.columns and 'pct_medicaid' in df_analysis.columns:
        corr = df_analysis['total_patients'].corr(df_analysis['pct_medicaid'])
        print(f"   📈 Correlation (Size vs Medicaid %): {corr:.2f}")
    
        # 3. Quick Terminal Histogram
        print("\n   Medicaid % Distribution (Deciles):")
        print(df_analysis['pct_medicaid'].quantile([0.1, 0.5, 0.9]))
    else:
        print("Columns missing for analysis.")

if __name__ == "__main__":
    analyze_data()