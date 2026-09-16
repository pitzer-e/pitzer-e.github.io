# Oregon FQHC Landscape: data contract and operation

## Definitions

- **Site count:** distinct nonmissing `BPHC Assigned Number` values (`site_id`) for records with Oregon site state and Active site status. Includes FQHC and FQHC Look-Alike registered sites. Not unique buildings, coordinates, addresses, or clinics inferred from names. Missing coordinates fail validation rather than reduce the headline population silently.
- **Organization count:** distinct nonmissing BHCMIS organization IDs among those sites. Names are display labels, not join keys.
- **Matched organization count:** those organization IDs found in the configured UDS Table4, regardless of whether a patient total is available.
- **Patient-data coverage:** report both (a) sites linked to an organization with a nonmissing reported total / all eligible sites and (b) organizations with such a total / all eligible organizations. Zero is a reported value and counts as available; its payer percentages remain undefined.
- **Patient total:** sum of reported 2024 organization totals, once per BHCMIS ID. It includes non-Oregon patients of multi-state organizations and may count a person across organizations. It is neither unique Oregon residents nor site-level volume.
- **Payer chart:** complete-case organizations with known total, Medicaid, and uninsured counts. Every slice uses this same population. Other insurance is the residual and includes other public insurance, Medicare, and private insurance.
- **Organization analysis:** one equally weighted observation per BHCMIS organization with a positive reported patient total and available Medicaid share. The primary size predictor is `log10(total_patients)`; no minimum-patient rule is imposed. The model is exploratory, not causal or a measure of patient-level effects or unmet need.

## Duplicate investigation

The former processed CSV contained two identical-looking rows for Cascadia Woodland Park Health Center. The source workbook contains two separate records: `BPS-LAL-032077` (Suite 125) and `BPS-LAL-032079` (Suite 200), with different NPIs and operating hours. Both share a name and geocoded point. Dropping identifiers and addresses created the apparent duplicate; the raw rows are not exact duplicates.

Keep both registered sites and preserve site ID/address. Duplicate site IDs now fail at the cleaning boundary for investigation. Duplicate UDS organization keys fail before joining. The merge declares a many-to-one relationship and verifies that site population and attributes are unchanged. Co-located map points may overlap; the table retains both records.

## Missingness and field mapping

The workbook Coversheet defines `-` as no entry, `--` as suppressed counts of 1–15, and `---` as confidential suppression. These and blank cells remain missing. Unknown nonnumeric values fail validation. No missing counts are imputed to zero, and suppression is not reverse-engineered from other totals.

Patient totals use `T4_L12_Ca + T4_L12_Cb` (insurance-section total across age groups), checked against `T4_L6_Ca` (income-section total) where both are reported. Uninsured uses `T4_L7_Ca + T4_L7_Cb`; Medicaid uses `T4_L8_Ca + T4_L8_Cb`. A missing component makes the sum missing. Percentages require a strictly positive denominator.

## Run from repository root

```sh
# Safe offline build from existing workbooks (freshness assessment still applies).
python projects/oregon-fqhc/scripts/run_pipeline.py --local

# Fetch both sources, validate and build a new complete snapshot.
python projects/oregon-fqhc/scripts/run_pipeline.py

python -m pytest -p no:cacheprovider projects/oregon-fqhc/tests/
python projects/oregon-fqhc/scripts/4_analyze_correlations.py
quarto render projects/oregon-fqhc/index.qmd
```

Use the repository virtual environment locally. Run dependencies are in the root requirements file. Dependencies remain unpinned; cross-version reproducibility is not guaranteed.

`1_ingest_data.py` is retained as a compatibility entry point to the downloaded-source pipeline (or `--local`). `2_clean_data.py` and `3_join_data.py` now rebuild the complete local snapshot; they no longer publish partially processed stages. Prefer the single runner. `4_analyze_correlations.py` is retained and used by CI: it validates the saved artifacts and prints the shared summary, rather than independently computing site-weighted statistics.

## Artifacts and failure behavior

- `oregon_sites.csv`: one eligible registered site per row.
- `oregon_sites_joined.csv`: same site population, enriched with organization metrics and explicit match/availability flags.
- `organizations.csv`: one row per organization represented by the sites, including unmatched organizations.
- `summary.json`: shared report metrics, computed from distinct organizations where appropriate.
- `manifest.json`: source URLs and hashes, source dates, build timestamp/mode, and output hashes.

Downloads and transformations run in staging. HTTP failures, invalid workbooks, schema changes, invalid metrics, unexplained join loss, or other hard integrity failures propagate as errors; existing artifacts are not overwritten on those failures. After validation, files are replaced atomically one at a time and the manifest is replaced last. This is not a database transaction: interruption during replacement can leave a mixed generation, but hash checks reject it and prevent rendering. Re-run the pipeline to recover.

The workflow runs weekly on Mondays or manually: build → tests → validate/report summary → render → commit outputs. Failed steps stop later steps. Only selected data and generated website paths are staged; commit failures are not swallowed. No workflow was dispatched as part of the local hardening work.

## Quality states and guardrails

- **Invalid / hard failure:** duplicate or missing required keys, unexpected join multiplication, impossible values, arithmetic disagreement, malformed provenance, mixed artifact generations, future-dated sources, or unexplained failure of FQHC organizations to match the configured H80 UDS source. Candidate artifacts do not replace the validated generation.
- **Valid with warning / reconciliation needed:** known source-scope gaps and operational anomalies remain visible. The current unmatched organizations are FQHC Look-Alikes outside the configured H80 workbook scope; their missing measures remain missing. Site coverage below **90%** is a reconciliation warning, not proof of invalid data.
- **Analytical review required:** organization analytical coverage below **85%** withholds the regression/correlation from the rendered report pending human review. Valid descriptive artifacts may still be produced. The threshold is an operational trigger against silent population loss, not a scientific cutoff.
- **Valid / normal:** integrity checks pass and no warning/review condition is present. Counts, coverage numerators and denominators, source dates, and reconciliation records are still reported.

## Annual snapshot and freshness

- The analytical cohort is explicitly **2024 UDS**. Annual source migration requires deliberate review; this pipeline does not assert that 2024 is the newest available cohort.
- The site footprint is a separately dated HRSA extract. It is not silently represented as contemporaneous with the 2024 UDS measures.
- Site source date comes from HRSA's `Data Warehouse Record Create Date`, not local modification time. A future date is invalid. Age greater than **14 days** raises an operational freshness warning; old data are not automatically invalid historical data.
- A local build records `retrieved_at_utc: null` and `source_mode: local_snapshot`; rebuilding cannot pretend a new download occurred.
- `freeze: false`, `cache: false`, and `error: false` apply only to this report. Each render executes the report, validates hashes and source freshness, and calculates from current saved artifacts. Existing frozen results cannot substitute for a new execution. Other case studies retain their existing behavior.
- Missing map rates use gray markers; numeric values remain missing. A dated static site is not automatically taken offline if a later scheduled refresh fails. Check Actions failures and the visible source dates before treating a published snapshot as current.

## Model choice and limitations

The primary model relates Medicaid share to `log10(total_patients)`. The transformation was selected before release because proportional differences better represent organizational scale and reduce geometric domination by the largest organization while retaining it. The pipeline also records raw Pearson, Spearman, HC3 uncertainty, and influence diagnostics. A larger coefficient or smaller p-value was not the selection rule. Substantial residual organization-level heterogeneity remains.

Future annual refreshes should review source scope, unmatched organizations, analytical coverage, size-distribution changes, coefficients, and influence before publication. A newer UDS year— including 2025—must be introduced separately rather than bundled with pipeline-method changes. No clinical impact, causal effect, site-level patient volume, or statewide resident total is inferred.
