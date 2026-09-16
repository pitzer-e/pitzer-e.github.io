"""Build and validate a complete snapshot before replacing published data artifacts."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile

import pandas as pd
import requests

from pipeline import ROOT, SOURCES, source_metadata, prepare_uds, join_sites, organization_frame, summarize, digest


def download_sources(destination):
    """Download into staging. HTTP/timeout/invalid workbook failures propagate."""
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    for name, url in SOURCES.items():
        response = requests.get(url, timeout=60, headers={'User-Agent': 'FQHC-portfolio-pipeline/1.0'})
        response.raise_for_status()
        (destination / name).write_bytes(response.content)


def build(root=ROOT, local=False, today=None):
    root = Path(root)
    data = root / 'data'
    data.mkdir(parents=True, exist_ok=True)
    # Staging lives on the same filesystem for atomic per-file replacement.
    # The manifest is replaced last; mixed/incomplete generations fail hash checks.
    with tempfile.TemporaryDirectory(prefix='.fqhc-build-', dir=data) as temporary:
        stage = Path(temporary)
        raw = data / 'raw' if local else stage / 'raw'
        if not local:
            download_sources(raw)
        sites, metadata = source_metadata(raw, today)
        uds = prepare_uds(pd.read_excel(raw / 'uds_2024.xlsx', sheet_name='Table4', dtype=str))
        joined = join_sites(sites, uds)
        orgs = organization_frame(joined)
        summary = summarize(joined)
        output = stage / 'processed'
        output.mkdir()
        for name, frame in [('oregon_sites.csv', sites), ('oregon_sites_joined.csv', joined), ('organizations.csv', orgs)]:
            frame.to_csv(output / name, index=False)
        (output / 'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n')
        metadata.update({
            'built_at_utc': datetime.now(timezone.utc).isoformat(),
            'source_mode': 'local_snapshot' if local else 'downloaded_this_run',
            'retrieved_at_utc': None if local else datetime.now(timezone.utc).isoformat(),
            'outputs': {p.name: digest(p) for p in sorted(output.iterdir())},
        })
        (output / 'manifest.json').write_text(json.dumps(metadata, indent=2) + '\n')
        # No existing raw or processed files are touched before all checks succeed.
        if not local:
            (data / 'raw').mkdir(exist_ok=True)
            for name in SOURCES:
                os.replace(raw / name, data / 'raw' / name)
        (data / 'processed').mkdir(exist_ok=True)
        for name in metadata['outputs']:
            os.replace(output / name, data / 'processed' / name)
        os.replace(output / 'manifest.json', data / 'processed' / 'manifest.json')
    return summary


def main(default_local=False):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--local', action='store_true', default=default_local, help='Use existing workbooks; do not claim a new retrieval')
    args = parser.parse_args()
    print(json.dumps(build(local=args.local), indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
