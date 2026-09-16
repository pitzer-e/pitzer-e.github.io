# Ethan Pitzer | Data Science & Analytics Engineering

![Pipeline Status](https://github.com/pitzer-e/pitzer-e.github.io/actions/workflows/daily_update.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

> **Welcome to my data science lab!** This repository hosts my data science case studies, automated data pipelines, and interactive dashboards.

**[Visit the Live Portfolio](https://pitzer-e.github.io/)**

---

## Repository Structure

This site is architected to separate deep-dive engineering work from visual analytics:

* **`projects/` (Case Studies):** Full-stack data engineering projects with Python pipelines, automated testing, and written analysis.
* **`dashboards/` (Visualizations):** Hosted Tableau/PowerBI embeds and interactive Plotly apps.
* **`projects/oregon-fqhc/tests/`:** Automated `pytest` suites ensuring data integrity before deployment.

---

## Featured Case Study: Oregon FQHC Landscape

A reproducible annual snapshot of Oregon's HRSA-reported health-center landscape. It combines a dated site-footprint extract with organization-level 2024 UDS measures, identifier-based joins, validation, and transparent analytical reporting.

### The Architecture
This project demonstrates a scheduled ETL pipeline with explicit validation gates running entirely on GitHub Actions:

1.  **Ingest:** Python scripts retrieve authoritative, separately dated source snapshots from the [HRSA Data Warehouse](https://data.hrsa.gov/) and FOIA reading rooms (2024 UDS patient measures). These are not live EHR counts.
2.  **Transform:** `pandas` performs cleaning, geospatial field standardization, and validated many-to-one joins. Current coverage and precise counting definitions are documented in the [project data contract](projects/oregon-fqhc/README.md).
3.  **Validate:** `pytest` separates hard integrity failures from visible reconciliation warnings and analytical-review triggers.
4.  **Analyze and publish:** One equally weighted row per organization supports an exploratory log-scale size/Medicaid-share model, and Quarto renders the static case study only from validated artifacts.

[**View the Full Case Study**](https://pitzer-e.github.io/projects/oregon-fqhc/)

## Featured Project: Clinic Service Forecaster

**Goal:** Predict future patient visit volumes to optimize staffing and budgeting for a community health center.

* **The Challenge:** Real patient data is HIPAA-restricted. I needed a way to demonstrate advanced forecasting capabilities without compromising privacy.
* **The Solution:**
    * **Synthetic Data Engineering:** Wrote Python scripts to generate 5 years of daily clinic data, incorporating realistic seasonality, weekly cycles, and "structural breaks" (e.g., COVID-19 lockdowns).
    * **Time Series Modeling:** Decomposed the data using **Statsmodels** to isolate trends and applied a **SARIMA** (Seasonal AutoRegressive Integrated Moving Average) model for 52-week forward predictions.
    * **Business Impact:** Translated model outputs into actionable strategies for dynamic staffing and resilience planning.
* **Tech Stack:** Python, Pandas, Statsmodels, Scikit-Learn, Seaborn, Quarto.

[**View the Full Case Study & Forecast**](https://pitzer-e.github.io/projects/clinic-forecasting/)

### Global Tech Stack
- Languages: Python, R, SQL
- Data Engineering: Pandas, Requests, Pytest, GitHub Actions
- Visualization: Plotly, Seaborn, Tableau
- Modeling: Statsmodels, Scikit-Learn
- Analysis: Time Series Decomposition, Forecasting
- Reporting: Quarto
