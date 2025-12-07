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
* **`tests/`:** Automated `pytest` suites ensuring data integrity before deployment.

---

## Featured Case Study: Oregon FQHC Landscape

A serverless, automated data product tracking Health Center Service Delivery Sites in Oregon. It replaces legacy manual workflows with a **Code-First approach**.

### The Architecture
This project demonstrates a production-grade ETL pipeline running entirely on GitHub Actions:

1.  **Ingest:** Python scripts fetch live data from the [HRSA Data Warehouse](https://data.hrsa.gov/) and FOIA reading rooms (UDS 2024 Patient Demographics).
2.  **Transform:** `pandas` performs cleaning, geospatial standardization, and deterministic joins (Match Rate: 97%).
3.  **Validate:** `pytest` acts as a quality gate, failing the build if data integrity checks (e.g., coordinate bounds, negative counts) are violated.
4.  **Publish:** Quarto renders the static site with interactive Plotly maps and statistical regression analysis.

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