"""Contract, regression, and failure-path tests for the FQHC data product."""
from datetime import date, timedelta
from pathlib import Path
import shutil
import sys

import numpy as np
import pandas as pd
import pytest
import requests

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
import pipeline as p
import run_pipeline as runner


@pytest.fixture(scope='session')
def snapshot():
    return p.load_artifacts()


@pytest.fixture
def joined(snapshot):
    return snapshot[0].copy()


@pytest.fixture
def sites(joined):
    return joined[list(p.SITE_COLUMNS.values())].copy()


@pytest.fixture(scope='session')
def raw_sites():
    return pd.read_excel(p.ROOT / 'data/raw/hrsa_sites.xlsx', dtype=str)


def test_persisted_snapshot_is_valid(snapshot):
    joined, orgs, summary, manifest = snapshot
    assert joined.site_id.is_unique
    assert orgs.bhcmis_id.is_unique
    assert summary == p.summarize(joined)
    assert manifest['uds_reporting_year'] == 2024


def test_colocated_registered_sites_are_not_duplicates():
    # Stable regression fixture: future source closures should not break this test.
    rows = []
    for i in range(12):
        row = {source: 'Example' for source in p.SITE_COLUMNS}
        row.update({'BPHC Assigned Number': f'BPS-{i:04d}',
                    'BHCMIS Organization Identification Number': '00123',
                    'Site State Abbreviation': 'OR', 'Site Status Description': 'Active',
                    'Geocoding Artifact Address Primary Y Coordinate': '45.536324',
                    'Geocoding Artifact Address Primary X Coordinate': '-122.555906',
                    'Data Warehouse Record Create Date': '09/14/2026',
                    'Site Address': f'10373 NE Hancock St Suite {i}'})
        rows.append(row)
    sites = p.clean_sites(pd.DataFrame(rows), today=date(2026, 9, 15))
    assert len(sites) == 12
    assert sites.site_id.is_unique
    assert sites.address.nunique() == 12
    assert sites.site_name.nunique() == 1
    assert sites[['latitude', 'longitude']].drop_duplicates().shape[0] == 1


def test_cleaning_rejects_repeated_site_identifier(raw_sites):
    row = raw_sites[raw_sites['Site State Abbreviation'].eq('OR')].iloc[[0]]
    with pytest.raises(ValueError, match='Duplicate site_id'):
        p.clean_sites(pd.concat([raw_sites, row], ignore_index=True))


@pytest.mark.parametrize('column', ['BPHC Assigned Number', 'Site Address', 'Site State Abbreviation'])
def test_required_source_schema(raw_sites, column):
    with pytest.raises(ValueError, match='Missing columns'):
        p.clean_sites(raw_sites.drop(columns=column))


def test_missing_coordinate_fails_instead_of_dropping_site(raw_sites):
    altered = raw_sites.copy()
    index = altered[altered['Site State Abbreviation'].eq('OR')].index[0]
    altered.loc[index, 'Geocoding Artifact Address Primary Y Coordinate'] = None
    with pytest.raises(ValueError, match='latitude'):
        p.clean_sites(altered)


def test_duplicate_organization_key_cannot_multiply_join(sites, snapshot):
    uds = snapshot[1][['bhcmis_id'] + p.METRICS]
    uds = pd.concat([uds, uds.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match='Duplicate bhcmis_id'):
        p.join_sites(sites, uds)


def test_unexpected_join_row_multiplication(sites, joined):
    extra = joined.iloc[[0]].copy()
    extra['site_id'] = 'unexpected-site'
    with pytest.raises(ValueError, match='population'):
        p.validate_joined(sites, pd.concat([joined, extra], ignore_index=True))


def test_site_fields_survive_join(sites, joined):
    joined.loc[0, 'address'] = 'wrong address'
    with pytest.raises(ValueError, match='site field address'):
        p.validate_joined(sites, joined)


def test_low_patient_coverage_is_visible_but_not_an_integrity_failure(sites, joined):
    ids = joined.loc[joined.uds_record_matched, 'bhcmis_id'].drop_duplicates().iloc[:15]
    rows = joined.bhcmis_id.isin(ids)
    joined.loc[rows, p.METRICS] = np.nan
    joined.loc[rows, 'patient_data_available'] = False
    p.validate_joined(sites, joined)
    quality = p.quality_assessment(joined)
    assert quality['site_patient_coverage'] < p.SITE_COVERAGE_WARNING_THRESHOLD
    assert any(warning['code'] == 'site_coverage_reconciliation' for warning in quality['warnings'])


def test_unmatched_data_remains_missing(joined):
    missing = joined[~joined.uds_record_matched]
    assert not missing.empty
    assert missing[p.METRICS].isna().all().all()


def test_zero_fill_of_unmatched_data_is_rejected(sites, joined):
    rows = ~joined.uds_record_matched
    joined.loc[rows, ['total_patients', 'uninsured', 'medicaid']] = 0
    joined.loc[rows, 'patient_data_available'] = True
    with pytest.raises(ValueError, match='remain missing'):
        p.validate_joined(sites, joined)


@pytest.mark.parametrize('value', [-0.1, 1.1, np.inf])
def test_payer_bounds(joined, value):
    joined.loc[0, 'pct_medicaid'] = value
    with pytest.raises(ValueError, match='outside'):
        p.validate_patient_metrics(joined)


def test_percentage_must_match_counts(joined):
    row = joined[joined.pct_medicaid.notna()].index[0]
    joined.loc[row, 'pct_medicaid'] = 0.123456
    with pytest.raises(ValueError, match='Inconsistent'):
        p.validate_patient_metrics(joined)


def test_negative_counts_rejected(joined):
    joined.loc[0, 'medicaid'] = -1
    with pytest.raises(ValueError, match='Invalid medicaid'):
        p.validate_patient_metrics(joined)


def uds_record(**changes):
    row = {'BHCMISID': '00123', 'T4_L6_Ca': '100', 'T4_L12_Ca': '40', 'T4_L12_Cb': '60',
           'T4_L7_Ca': '5', 'T4_L7_Cb': '5', 'T4_L8_Ca': '20', 'T4_L8_Cb': '30'}
    row.update(changes)
    return pd.DataFrame([row])


def test_suppression_is_not_zero():
    data = p.prepare_uds(uds_record(T4_L7_Ca='--'))
    assert pd.isna(data.uninsured.iloc[0])
    assert pd.isna(data.pct_uninsured.iloc[0])
    assert data.medicaid.iloc[0] == 50
    assert data.bhcmis_id.iloc[0] == '00123'


def test_zero_denominator_remains_missing():
    data = p.prepare_uds(uds_record(**{c: '0' for c in p.PAYER_INPUTS}))
    assert data[['pct_uninsured', 'pct_medicaid']].isna().all().all()


def test_unknown_numeric_token_rejected():
    with pytest.raises(ValueError, match='Unrecognized'):
        p.prepare_uds(uds_record(T4_L7_Ca='changed schema'))


def test_disagreeing_total_sections_rejected():
    with pytest.raises(ValueError, match='totals disagree'):
        p.prepare_uds(uds_record(T4_L6_Ca='101'))


def test_organization_statistics_are_not_site_weighted(joined):
    before = p.summarize(joined)
    extra = joined[joined.patient_data_available].iloc[[0]].copy()
    extra['site_id'] = 'synthetic-additional-site'
    after = p.summarize(pd.concat([joined, extra], ignore_index=True))
    for key in ['organization_count', 'reported_organization_patient_total', 'analysis_model', 'medicaid_percentiles']:
        assert before[key] == after[key]
    assert after['site_count'] == before['site_count'] + 1


def test_conflicting_repeated_org_metrics_rejected(joined):
    row = joined[joined.bhcmis_id.duplicated(False)].index[0]
    joined.loc[row, 'total_patients'] = 1
    with pytest.raises(ValueError, match='Conflicting organization'):
        p.organization_frame(joined)


def test_stale_site_source_is_warning_not_hard_failure():
    today = date(2026, 9, 15)
    quality = p.check_site_date((today - timedelta(days=15)).isoformat(), today)
    assert quality['status'] == 'warning'
    assert quality['warning']


def test_future_site_source_is_hard_failure():
    today = date(2026, 9, 15)
    with pytest.raises(ValueError, match='future-dated'):
        p.check_site_date((today + timedelta(days=1)).isoformat(), today)


def test_source_freshness_boundary():
    assert p.check_site_date('2026-09-01', date(2026, 9, 15))['status'] == 'normal'


def test_failed_download_keeps_existing_snapshot(tmp_path, monkeypatch):
    output = tmp_path / 'data/processed'
    output.mkdir(parents=True)
    sentinel = output / 'manifest.json'
    sentinel.write_text('existing valid generation')
    def fail(*args, **kwargs):
        raise requests.Timeout('simulated timeout')
    monkeypatch.setattr(runner.requests, 'get', fail)
    with pytest.raises(requests.Timeout):
        runner.build(tmp_path)
    assert sentinel.read_text() == 'existing valid generation'
    assert not list((tmp_path / 'data').glob('.fqhc-build-*'))


def test_invalid_download_does_not_replace_raw_or_outputs(tmp_path, monkeypatch):
    raw = tmp_path / 'data/raw'
    raw.mkdir(parents=True)
    sentinel = raw / 'hrsa_sites.xlsx'
    sentinel.write_bytes(b'previous workbook')
    class Response:
        content = b'<html>not an Excel workbook</html>'
        def raise_for_status(self):
            pass
    monkeypatch.setattr(runner.requests, 'get', lambda *a, **k: Response())
    with pytest.raises(ValueError):
        runner.build(tmp_path)
    assert sentinel.read_bytes() == b'previous workbook'
    assert not (tmp_path / 'data/processed/manifest.json').exists()


def test_manifest_detects_source_and_output_changes(tmp_path, snapshot):
    shutil.copytree(p.ROOT / 'data', tmp_path / 'data')
    source = tmp_path / 'data/raw/hrsa_sites.xlsx'
    old = source.read_bytes()
    source.write_bytes(b'changed workbook')
    with pytest.raises(ValueError, match='Source changed'):
        p.load_artifacts(tmp_path)
    source.write_bytes(old)
    (tmp_path / 'data/processed/summary.json').write_text('{}')
    with pytest.raises(ValueError, match='Output changed'):
        p.load_artifacts(tmp_path)


def test_fqhc_execution_is_not_frozen():
    source = (p.ROOT / 'index.qmd').read_text()
    assert 'freeze: false' in source
    assert 'cache: false' in source
    assert 'load_artifacts' in source


def test_organization_coverage_triggers_analytical_review(sites, joined):
    counts = joined.groupby('bhcmis_id').size().sort_values()
    # Keep site coverage high while losing several small organizations.
    eligible = joined.loc[joined.uds_record_matched, 'bhcmis_id'].drop_duplicates()
    ids = [value for value in counts.index if value in set(eligible)][:6]
    rows = joined.bhcmis_id.isin(ids)
    joined.loc[rows, p.METRICS] = np.nan
    joined.loc[rows, 'patient_data_available'] = False
    assert joined.patient_data_available.mean() >= p.SITE_COVERAGE_WARNING_THRESHOLD
    p.validate_joined(sites, joined)
    quality = p.quality_assessment(joined)
    assert quality['status'] == 'ANALYTICAL_REVIEW_REQUIRED'
    assert not quality['analysis_publishable']
    assert quality['organization_analytical_coverage'] < p.ANALYTICAL_REVIEW_THRESHOLD


def test_unexplained_match_loss_is_hard_failure(sites, joined):
    org_id = joined.loc[joined['type'].eq('Federally Qualified Health Center (FQHC)'), 'bhcmis_id'].iloc[0]
    rows = joined.bhcmis_id.eq(org_id)
    joined.loc[rows, p.METRICS] = np.nan
    joined.loc[rows, ['uds_record_matched', 'patient_data_available']] = False
    with pytest.raises(ValueError, match='Unexplained organization match loss'):
        p.validate_joined(sites, joined)


def test_known_lookalike_gap_is_reconciled(joined):
    reconciled = p.reconcile_unmatched_organizations(joined)
    assert {item['organization'] for item in reconciled} == {'CASCADE AIDS PROJECT', 'CASCADIA HEALTH'}
    assert all(item['reconciliation'] == 'outside_configured_h80_uds_scope' for item in reconciled)


def test_analysis_has_no_arbitrary_minimum_and_requires_positive_denominator():
    orgs = pd.DataFrame([
        {'bhcmis_id': 'small', 'organization': 'Small valid org', 'total_patients': 50.0, 'pct_medicaid': 0.5},
        {'bhcmis_id': 'zero', 'organization': 'Zero denominator', 'total_patients': 0.0, 'pct_medicaid': np.nan},
        {'bhcmis_id': 'missing', 'organization': 'Missing share', 'total_patients': 500.0, 'pct_medicaid': np.nan},
    ])
    analysis = p.analysis_population(orgs)
    assert analysis.bhcmis_id.tolist() == ['small']
    assert analysis.log10_total_patients.iloc[0] == pytest.approx(np.log10(50))


def test_primary_model_is_equal_weight_log10_and_summary_counts_are_explicit(snapshot):
    _, _, summary, _ = snapshot
    model = summary['analysis_model']
    quality = summary['quality']
    assert model['predictor'] == 'log10_total_patients'
    assert model['weighting'] == 'equal_organization'
    assert model['pearson_r'] == pytest.approx(0.5305686274)
    assert model['r_squared'] == pytest.approx(model['pearson_r'] ** 2)
    assert model['spearman_rho'] == pytest.approx(0.4633064516)
    assert quality['site_patient_coverage_numerator'] == summary['patient_data_site_count']
    assert quality['site_patient_coverage_denominator'] == summary['site_count']
    assert quality['organization_patient_coverage_denominator'] == summary['organization_count']
    assert quality['organization_analytical_coverage_numerator'] == summary['analysis_organization_count']


def test_transformation_failure_preserves_old_outputs(tmp_path, monkeypatch, sites):
    output = tmp_path / 'data/processed'
    output.mkdir(parents=True)
    sentinel = output / 'manifest.json'
    sentinel.write_text('previous generation')
    monkeypatch.setattr(runner, 'source_metadata', lambda *args: (sites, {}))
    monkeypatch.setattr(runner.pd, 'read_excel', lambda *args, **kwargs: uds_record())
    def fail(*args):
        raise ValueError('simulated transformation failure')
    monkeypatch.setattr(runner, 'join_sites', fail)
    with pytest.raises(ValueError, match='transformation failure'):
        runner.build(tmp_path, local=True)
    assert sentinel.read_text() == 'previous generation'
