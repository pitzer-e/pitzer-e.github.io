"""Shared FQHC data contracts, transformations, and validated artifact loading."""
from datetime import date, datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import re

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    'hrsa_sites.xlsx': 'https://data.hrsa.gov/DataDownload/DD_Files/Health_Center_Service_Delivery_and_LookAlike_Sites.xlsx',
    'uds_2024.xlsx': 'https://www.hrsa.gov/sites/default/files/hrsa/foia/h80-2024.xlsx',
}
UDS_YEAR = 2024
SITE_FRESHNESS_WARNING_DAYS = 14
SITE_COVERAGE_WARNING_THRESHOLD = 0.90
ANALYTICAL_REVIEW_THRESHOLD = 0.85
SITE_COLUMNS = {
    'BPHC Assigned Number': 'site_id',
    'BHCMIS Organization Identification Number': 'bhcmis_id',
    'Health Center Name': 'organization', 'Site Name': 'site_name',
    'Site Address': 'address', 'Site City': 'city',
    'County Equivalent Name': 'county', 'Health Center Type': 'type',
    'Site Status Description': 'status',
    'Geocoding Artifact Address Primary Y Coordinate': 'latitude',
    'Geocoding Artifact Address Primary X Coordinate': 'longitude',
    'Data Warehouse Record Create Date': 'source_date',
}
PAYER_INPUTS = ['T4_L6_Ca', 'T4_L12_Ca', 'T4_L12_Cb', 'T4_L7_Ca', 'T4_L7_Cb', 'T4_L8_Ca', 'T4_L8_Cb']
METRICS = ['total_patients', 'uninsured', 'medicaid', 'pct_uninsured', 'pct_medicaid']
MISSING_MARKERS = {'', '-', '--', '---'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def normalize_ids(values):
    # String dtype preserves leading zeroes and genuine nulls.
    return values.astype('string').str.strip().str.replace(r'\.0$', '', regex=True).replace('', pd.NA)


def require_columns(df, columns):
    require(set(columns) <= set(df), f'Missing columns: {sorted(set(columns) - set(df))}')


def require_unique(df, key):
    require_columns(df, [key])
    require(df[key].notna().all(), f'Missing {key}')
    require(not df[key].duplicated().any(), f'Duplicate {key}: {df.loc[df[key].duplicated(False), key].tolist()}')


def check_site_date(value, today=None):
    today = today or datetime.now(timezone.utc).date()
    age = (today - date.fromisoformat(value)).days
    require(age >= 0, f'Site source date {value} is future-dated')
    return {
        'age_days': age,
        'status': 'warning' if age > SITE_FRESHNESS_WARNING_DAYS else 'normal',
        'warning': None if age <= SITE_FRESHNESS_WARNING_DAYS else
            f'Site source date is {age} days old; review expected refresh timing before describing the snapshot as current.',
    }


def clean_sites(raw, today=None):
    raw = raw.copy()
    raw.columns = raw.columns.str.strip()
    require_columns(raw, list(SITE_COLUMNS) + ['Site State Abbreviation'])
    sites = raw.loc[raw['Site State Abbreviation'].eq('OR') & raw['Site Status Description'].eq('Active'), list(SITE_COLUMNS)].rename(columns=SITE_COLUMNS).copy()
    for key in ['site_id', 'bhcmis_id']:
        sites[key] = normalize_ids(sites[key])
    # Never deduplicate by name/address/coordinates: separate registered sites may be co-located.
    require_unique(sites, 'site_id')
    require(sites['bhcmis_id'].notna().all(), 'Missing organization identifier')
    require(len(sites) > 10, 'Suspiciously small Oregon site dataset')
    for col in ['organization', 'site_name', 'address']:
        require(sites[col].notna().all() and sites[col].astype(str).str.strip().ne('').all(), f'Missing {col}')
    for col, limits in [('latitude', (41, 47)), ('longitude', (-125, -116))]:
        sites[col] = pd.to_numeric(sites[col], errors='raise')
        require(sites[col].between(*limits).all(), f'Missing or out-of-region {col}; do not silently drop sites')
    dates = pd.to_datetime(sites['source_date'], format='%m/%d/%Y', errors='raise')
    require(dates.notna().all() and dates.nunique() == 1, 'Missing or inconsistent site source dates')
    source_date = dates.iloc[0].date().isoformat()
    check_site_date(source_date, today)
    sites['source_date'] = source_date
    require(sites.groupby('bhcmis_id')['organization'].nunique().le(1).all(), 'Conflicting organization names for one ID')
    return sites.sort_values('site_id').reset_index(drop=True)


def parse_counts(values, column):
    text = values.astype('string').str.strip()
    missing = text.isna() | text.isin(MISSING_MARKERS)
    numeric = pd.to_numeric(text.mask(missing), errors='coerce').astype(float)
    require(not (numeric.isna() & ~missing).any(), f'Unrecognized numeric value in {column}')
    require(numeric.dropna().ge(0).all() and np.isfinite(numeric.dropna()).all(), f'Invalid count in {column}')
    require(numeric.dropna().mod(1).eq(0).all(), f'Non-integer patient count in {column}')
    return numeric


def prepare_uds(raw):
    require_columns(raw, ['BHCMISID'] + PAYER_INPUTS)
    raw = raw.copy()
    raw['BHCMISID'] = normalize_ids(raw['BHCMISID'])
    # HRSA includes one non-record field-description row with no organization ID.
    descriptions = raw['BHCMISID'].isna()
    require(descriptions.sum() <= 1, 'Unexpected number of UDS rows without IDs')
    if descriptions.any():
        require(raw.loc[descriptions, 'T4_L6_Ca'].astype(str).str.contains('TOTAL', case=False).all(), 'Unidentified UDS row without ID')
    raw = raw.loc[~descriptions].copy()
    require_unique(raw, 'BHCMISID')
    require(raw['BHCMISID'].str.fullmatch(r'[0-9A-Za-z]+').all(), 'Malformed UDS organization ID')
    counts = pd.DataFrame({c: parse_counts(raw[c], c) for c in PAYER_INPUTS})
    out = pd.DataFrame({'bhcmis_id': raw['BHCMISID']})
    # Use insurance-section total for payer denominators; reconcile to income-section total when available.
    out['total_patients'] = counts['T4_L12_Ca'] + counts['T4_L12_Cb']
    known = counts['T4_L6_Ca'].notna() & out['total_patients'].notna()
    require(counts.loc[known, 'T4_L6_Ca'].eq(out.loc[known, 'total_patients']).all(), 'UDS patient totals disagree across sections')
    out['uninsured'] = counts['T4_L7_Ca'] + counts['T4_L7_Cb']
    out['medicaid'] = counts['T4_L8_Ca'] + counts['T4_L8_Cb']
    denominator = out['total_patients'].where(out['total_patients'] > 0)
    for col in ['uninsured', 'medicaid']:
        out['pct_' + col] = out[col] / denominator
    validate_patient_metrics(out)
    return out.reset_index(drop=True)


def validate_patient_metrics(df):
    require_columns(df, METRICS)
    for col in ['total_patients', 'uninsured', 'medicaid']:
        known = df[col].dropna()
        require(np.isfinite(known).all() and known.ge(0).all(), f'Invalid {col}')
    for col in ['uninsured', 'medicaid']:
        known = df[['total_patients', col]].dropna()
        require(known[col].le(known['total_patients']).all(), f'{col} exceeds total patients')
        pct = df['pct_' + col]
        require(pct.dropna().between(0, 1).all(), f'{col} percentage outside [0, 1]')
        expected = df[col] / df['total_patients'].where(df['total_patients'] > 0)
        require(np.allclose(pct, expected, equal_nan=True), f'Inconsistent {col} percentage')
    known = df[['total_patients', 'uninsured', 'medicaid']].dropna()
    require((known['uninsured'] + known['medicaid']).le(known['total_patients']).all(), 'Payer subtotal exceeds total patients')


def join_sites(sites, uds):
    require_unique(sites, 'site_id')
    require_unique(uds, 'bhcmis_id')
    joined = sites.merge(uds, on='bhcmis_id', how='left', validate='many_to_one', indicator=True)
    require(len(joined) == len(sites), 'Join multiplied site rows')
    joined['uds_record_matched'] = joined.pop('_merge').eq('both')
    joined['patient_data_available'] = joined['total_patients'].notna()
    validate_joined(sites, joined)
    return joined


def organization_frame(joined):
    columns = ['organization', 'uds_record_matched', 'patient_data_available'] + METRICS
    require(joined.groupby('bhcmis_id')[columns].nunique(dropna=False).le(1).all().all(), 'Conflicting organization metrics across sites')
    return joined[['bhcmis_id'] + columns].drop_duplicates('bhcmis_id').sort_values('bhcmis_id').reset_index(drop=True)


def reconcile_unmatched_organizations(joined):
    """Explain source-scope gaps and reject unexplained identifier/join loss."""
    records = []
    unexpected = []
    for (org_id, name), rows in joined.loc[~joined.uds_record_matched].groupby(['bhcmis_id', 'organization']):
        types = sorted(rows['type'].dropna().unique().tolist())
        lookalike_only = bool(types) and all('Look-Alike' in value for value in types)
        record = {
            'bhcmis_id': str(org_id),
            'organization': name,
            'site_count': int(len(rows)),
            'site_types': types,
            'reconciliation': 'outside_configured_h80_uds_scope' if lookalike_only else 'unexplained_match_loss',
        }
        records.append(record)
        if not lookalike_only:
            unexpected.append(record)
    require(not unexpected, f'Unexplained organization match loss: {unexpected}')
    return records


def validate_joined(sites, joined):
    require_unique(joined, 'site_id')
    require(len(sites) == len(joined) and set(sites.site_id) == set(joined.site_id), 'Join changed site population')
    for col in sites.columns:
        a = sites.set_index('site_id').sort_index()[col] if col != 'site_id' else None
        if a is not None:
            b = joined.set_index('site_id').sort_index()[col]
            require(a.equals(b), f'Join changed site field {col}')
    validate_patient_metrics(joined)
    require(joined['patient_data_available'].eq(joined.total_patients.notna()).all(), 'Patient availability flag disagrees with data')
    unmatched = ~joined.uds_record_matched
    require(joined.loc[unmatched, METRICS].isna().all().all(), 'Unmatched patient information must remain missing')
    organization_frame(joined)
    reconcile_unmatched_organizations(joined)


def analysis_population(orgs):
    eligible = orgs.loc[(orgs.total_patients > 0) & orgs.pct_medicaid.notna()].copy()
    eligible['log10_total_patients'] = np.log10(eligible['total_patients'])
    return eligible


def analytical_model(orgs):
    """Fit the prespecified, equal-organization log-size model and diagnostics."""
    trend = analysis_population(orgs)
    if len(trend) < 3 or trend.log10_total_patients.nunique() < 2 or trend.pct_medicaid.nunique() < 2:
        return None

    y = trend['pct_medicaid'].astype(float)
    x_log = trend['log10_total_patients'].astype(float)
    x_raw = trend['total_patients'].astype(float)
    model = sm.OLS(y, sm.add_constant(x_log.rename('log10_total_patients'))).fit()
    raw_model = sm.OLS(y, sm.add_constant(x_raw.rename('total_patients'))).fit()
    robust = model.get_robustcov_results(cov_type='HC3')
    pearson = stats.pearsonr(x_log, y)
    raw_pearson = stats.pearsonr(x_raw, y)
    spearman = stats.spearmanr(x_raw, y)
    slope_ci = model.conf_int().loc['log10_total_patients'].tolist()
    robust_ci = robust.conf_int()[1].tolist()
    doubling_factor = np.log10(2)

    influence = model.get_influence().summary_frame()
    raw_influence = raw_model.get_influence().summary_frame()
    yakima = trend['organization'].eq('YAKIMA VALLEY FARM WORKERS CLINIC')
    yakima_diagnostics = None
    if yakima.any():
        position = int(np.flatnonzero(yakima.to_numpy())[0])
        yakima_diagnostics = {
            'bhcmis_id': str(trend.iloc[position].bhcmis_id),
            'organization': trend.iloc[position].organization,
            'raw_leverage': float(raw_influence.iloc[position].hat_diag),
            'log10_leverage': float(influence.iloc[position].hat_diag),
            'raw_cooks_distance': float(raw_influence.iloc[position].cooks_d),
            'log10_cooks_distance': float(influence.iloc[position].cooks_d),
        }

    return {
        'predictor': 'log10_total_patients',
        'response': 'pct_medicaid',
        'observational_unit': 'bhcmis_organization',
        'weighting': 'equal_organization',
        'pearson_r': float(pearson.statistic),
        'pearson_p_value': float(pearson.pvalue),
        'pearson_ci95': [float(value) for value in pearson.confidence_interval(0.95)],
        'r_squared': float(model.rsquared),
        'intercept': float(model.params['const']),
        'slope_per_tenfold_increase': float(model.params['log10_total_patients']),
        'slope_ci95': [float(value) for value in slope_ci],
        'slope_p_value': float(model.pvalues['log10_total_patients']),
        'hc3_slope_ci95': [float(value) for value in robust_ci],
        'hc3_slope_p_value': float(robust.pvalues[1]),
        'doubling_effect': float(model.params['log10_total_patients'] * doubling_factor),
        'doubling_effect_ci95': [float(value * doubling_factor) for value in slope_ci],
        'spearman_rho': float(spearman.statistic),
        'spearman_p_value': float(spearman.pvalue),
        'raw_pearson_r': float(raw_pearson.statistic),
        'raw_pearson_p_value': float(raw_pearson.pvalue),
        'raw_r_squared': float(raw_model.rsquared),
        'yakima_influence': yakima_diagnostics,
    }


def quality_assessment(joined):
    orgs = organization_frame(joined)
    analysis = analysis_population(orgs)
    site_numerator = int(joined.patient_data_available.sum())
    site_denominator = int(len(joined))
    org_numerator = int(orgs.patient_data_available.sum())
    org_denominator = int(len(orgs))
    analytical_numerator = int(len(analysis))
    analytical_denominator = org_denominator
    site_coverage = site_numerator / site_denominator
    org_coverage = org_numerator / org_denominator
    analytical_coverage = analytical_numerator / analytical_denominator
    reconciled = reconcile_unmatched_organizations(joined)
    warnings = []
    if reconciled:
        warnings.append({
            'code': 'known_source_scope_gap',
            'message': f'{len(reconciled)} Look-Alike organizations are outside the configured H80 UDS source scope.',
        })
    if site_coverage < SITE_COVERAGE_WARNING_THRESHOLD:
        warnings.append({
            'code': 'site_coverage_reconciliation',
            'message': f'Site patient-data coverage {site_coverage:.1%} is below the {SITE_COVERAGE_WARNING_THRESHOLD:.0%} operational review trigger.',
        })
    review_required = analytical_coverage < ANALYTICAL_REVIEW_THRESHOLD
    if review_required:
        warnings.append({
            'code': 'analytical_population_review',
            'message': f'Organization analytical coverage {analytical_coverage:.1%} is below the {ANALYTICAL_REVIEW_THRESHOLD:.0%} operational review trigger; withhold model publication pending human review.',
        })
    status = 'ANALYTICAL_REVIEW_REQUIRED' if review_required else ('VALID_WITH_WARNING' if warnings else 'VALID_NORMAL')
    return {
        'status': status,
        'analysis_publishable': not review_required,
        'warnings': warnings,
        'reconciled_unmatched_organizations': reconciled,
        'site_patient_coverage_numerator': site_numerator,
        'site_patient_coverage_denominator': site_denominator,
        'site_patient_coverage': float(site_coverage),
        'organization_patient_coverage_numerator': org_numerator,
        'organization_patient_coverage_denominator': org_denominator,
        'organization_patient_coverage': float(org_coverage),
        'organization_analytical_coverage_numerator': analytical_numerator,
        'organization_analytical_coverage_denominator': analytical_denominator,
        'organization_analytical_coverage': float(analytical_coverage),
    }


def summarize(joined):
    orgs = organization_frame(joined)
    trend = analysis_population(orgs)
    complete = orgs.dropna(subset=['total_patients', 'uninsured', 'medicaid'])
    q = trend.pct_medicaid.quantile([0.1, 0.5, 0.9])
    quality = quality_assessment(joined)
    return {
        'site_count': int(joined.site_id.nunique()),
        'organization_count': len(orgs),
        'matched_organization_count': int(orgs.uds_record_matched.sum()),
        'patient_data_organization_count': quality['organization_patient_coverage_numerator'],
        'patient_data_site_count': quality['site_patient_coverage_numerator'],
        'site_patient_coverage': quality['site_patient_coverage'],
        'organization_patient_coverage': quality['organization_patient_coverage'],
        'reported_organization_patient_total': float(orgs.total_patients.sum(min_count=1)),
        'complete_payer_organization_count': len(complete),
        'complete_payer_patient_total': float(complete.total_patients.sum(min_count=1)),
        'analysis_organization_count': len(trend),
        'analysis_model': analytical_model(orgs),
        'medicaid_percentiles': {str(p): None if pd.isna(q[p]) else float(q[p]) for p in q.index},
        'quality': quality,
    }


def source_metadata(raw_dir, today=None):
    raw_dir = Path(raw_dir)
    sites = clean_sites(pd.read_excel(raw_dir / 'hrsa_sites.xlsx', dtype=str), today)
    cover = pd.read_excel(raw_dir / 'uds_2024.xlsx', sheet_name='Coversheet', dtype=str)
    require_columns(cover, ['ReportingYear', 'DateOfLastReportRefresh'])
    year = pd.to_numeric(cover['ReportingYear'], errors='coerce').dropna().unique()
    require(len(year) == 1 and year[0] == UDS_YEAR, 'Unexpected UDS reporting year; review source configuration')
    refreshed = str(cover['DateOfLastReportRefresh'].dropna().iloc[0])
    require(re.match(r'\d{2}/\d{2}/\d{4}', refreshed) is not None, 'Missing UDS refresh date')
    refresh_date = datetime.strptime(refreshed[:10], '%m/%d/%Y').date()
    require(refresh_date <= (today or datetime.now(timezone.utc).date()), 'Future UDS refresh date')
    site_date_quality = check_site_date(sites.source_date.iloc[0], today)
    return sites, {
        'site_source_date': sites.source_date.iloc[0],
        'site_source_age_days_at_build': site_date_quality['age_days'],
        'site_freshness_status_at_build': site_date_quality['status'],
        'provenance_warnings': [] if site_date_quality['warning'] is None else [site_date_quality['warning']],
        'uds_reporting_year': UDS_YEAR,
        'uds_source_refresh_date': refresh_date.isoformat(),
        'sources': {name: {'url': url, 'sha256': digest(raw_dir / name)} for name, url in SOURCES.items()},
    }


def load_artifacts(root=ROOT, today=None):
    root = Path(root)
    output = root / 'data' / 'processed'
    manifest = json.loads((output / 'manifest.json').read_text())
    require(set(manifest['sources']) == set(SOURCES), 'Manifest missing source fingerprints')
    require(set(manifest['outputs']) == {'oregon_sites.csv', 'oregon_sites_joined.csv', 'organizations.csv', 'summary.json'}, 'Manifest missing output fingerprints')
    site_date_quality = check_site_date(manifest['site_source_date'], today)
    manifest['current_site_source_age_days'] = site_date_quality['age_days']
    manifest['current_site_freshness_status'] = site_date_quality['status']
    manifest['current_provenance_warnings'] = [] if site_date_quality['warning'] is None else [site_date_quality['warning']]
    require(manifest['uds_reporting_year'] == UDS_YEAR, 'Unexpected reporting year')
    for name, details in manifest['sources'].items():
        require(digest(root / 'data' / 'raw' / name) == details['sha256'], f'Source changed since pipeline run: {name}')
    for name, expected in manifest['outputs'].items():
        require(digest(output / name) == expected, f'Output changed or incomplete pipeline run: {name}')
    dtype = {'site_id': 'string', 'bhcmis_id': 'string'}
    sites = pd.read_csv(output / 'oregon_sites.csv', dtype=dtype, float_precision='round_trip')
    joined = pd.read_csv(output / 'oregon_sites_joined.csv', dtype=dtype, float_precision='round_trip')
    validate_joined(sites, joined)
    expected = summarize(joined)
    require(json.loads((output / 'summary.json').read_text()) == expected, 'Summary disagrees with data')
    saved_orgs = pd.read_csv(output / 'organizations.csv', dtype={'bhcmis_id': 'string'}, float_precision='round_trip')
    pd.testing.assert_frame_equal(saved_orgs, organization_frame(joined), check_dtype=False)
    return joined, saved_orgs, expected, manifest
