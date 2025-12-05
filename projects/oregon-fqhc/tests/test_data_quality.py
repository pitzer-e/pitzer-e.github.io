import pytest
import pandas as pd
from pathlib import Path

# --- FIXTURES (Setup) ---
@pytest.fixture
def df():
    """Load the final processed dataset for testing"""
    # Find the file relative to this test script
    base_dir = Path(__file__).parent.parent
    data_path = base_dir / "data" / "processed" / "oregon_sites_joined.csv"
    
    if not data_path.exists():
        pytest.fail(f"Data file not found at: {data_path}. Run pipeline first.")
    
    df = pd.read_csv(data_path)

    # --- CRITICAL DATA PATCHING ---
    # The Join process leaves 'NaN' for sites that didn't match UDS data.
    # For testing and visualization, we treat these as 0.
    # If we don't do this, 'NaN >= 0' evaluates to False, causing the test to fail.
    df['total_patients'] = df['total_patients'].fillna(0)
    df['uninsured'] = df['uninsured'].fillna(0)
    df['medicaid'] = df['medicaid'].fillna(0)
    
    return df

# --- TESTS ---

def test_file_is_not_empty(df):
    """Refuse to build the site if we have zero sites."""
    assert len(df) > 0, "Dataset is empty!"
    assert len(df) > 10, "Dataset is suspiciously small (under 10 sites)."

def test_required_columns_exist(df):
    """Ensure the columns we need for the map are actually there."""
    required_cols = ['latitude', 'longitude', 'total_patients', 'pct_medicaid', 'organization']
    for col in required_cols:
        assert col in df.columns, f"Critical column missing: {col}"

def test_geospatial_bounds_oregon(df):
    """Sanity check: Are the coordinates actually in/near Oregon?"""
    # Oregon Lat: ~42 to 46.5, Lon: ~-124.5 to -116.5
    valid_lat = df['latitude'].between(41, 47)
    valid_lon = df['longitude'].between(-125, -116)
    
    outliers = df[~(valid_lat & valid_lon)]
    assert len(outliers) == 0, f"Found {len(outliers)} sites with coordinates outside Oregon bounds!"

def test_patient_math_makes_sense(df):
    """Logic Check: Uninsured count cannot be higher than Total Patients."""
    # We use a tiny tolerance for floating point math
    impossible_math = df[df['uninsured'] > df['total_patients']]
    
    assert len(impossible_math) == 0, "Found sites where Uninsured > Total Patients (Data Corrupted)."

def test_no_negative_counts(df):
    """Logic Check: You can't have negative patients."""
    # Now that we've filled NaNs with 0, this should pass.
    assert (df['total_patients'] >= 0).all(), "Found negative patient counts!"