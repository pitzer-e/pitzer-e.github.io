# Ethan Pitzer | Data Science & Analytics Engineering

![Pipeline Status](https://github.com/pitzer-e/pitzer-e.github.io/actions/workflows/daily_update.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

> **Welcome to my engineering lab.** This repository hosts my technical case studies, automated data pipelines, and interactive dashboards.

**[🌐 Visit the Live Portfolio](https://pitzer-e.github.io/)**

---

## 📂 Repository Structure

This site is architected to separate deep-dive engineering work from visual analytics:

* **`projects/` (Case Studies):** Full-stack data engineering projects with Python pipelines, automated testing, and written analysis.
* **`dashboards/` (Visualizations):** Hosted Tableau/PowerBI embeds and interactive Plotly apps.
* **`tests/`:** Automated `pytest` suites ensuring data integrity before deployment.

---

## 🌲 Featured Case Study: Oregon FQHC Landscape

**[View the Live Project](https://pitzer-e.github.io/projects/oregon-fqhc/)**

A serverless, automated data product tracking Health Center Service Delivery Sites in Oregon. It replaces legacy manual workflows with a **Code-First approach**.

### The Architecture
This project demonstrates a production-grade ETL pipeline running entirely on GitHub Actions:

1.  **Ingest:** Python scripts fetch live data from the [HRSA Data Warehouse](https://data.hrsa.gov/) and FOIA reading rooms (UDS 2024 Patient Demographics).
2.  **Transform:** `pandas` performs cleaning, geospatial standardization, and deterministic joins (Match Rate: 97%).
3.  **Validate:** `pytest` acts as a quality gate, failing the build if data integrity checks (e.g., coordinate bounds, negative counts) are violated.
4.  **Publish:** Quarto renders the static site with interactive Plotly maps and statistical regression analysis.

### Quick Start (Run the Pipeline Locally)

Want to see the engineering in action?

```bash
# 1. Clone & Install
git clone [https://github.com/pitzer-e/pitzer-e.github.io.git](https://github.com/pitzer-e/pitzer-e.github.io.git)
pip install -r requirements.txt

# 2. Run the ETL Pipeline
python projects/oregon-fqhc/scripts/1_ingest_data.py
python projects/oregon-fqhc/scripts/2_clean_data.py
python projects/oregon-fqhc/scripts/3_join_data.py

# 3. Run Quality Assurance Tests
pytest projects/oregon-fqhc/tests/
```

### 🛠 Global Tech Stack
- Languages: Python, R, SQL
- Data Engineering: Pandas, Requests, Pytest, GitHub Actions
- Visualization: Plotly, Seaborn, Tableau, Quarto