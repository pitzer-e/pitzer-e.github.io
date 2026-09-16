"""Validate the saved snapshot and report the shared organization-level summary."""
import json
from pipeline import load_artifacts

if __name__ == '__main__':
    _, _, summary, _ = load_artifacts()
    print(json.dumps(summary, indent=2, allow_nan=False))
