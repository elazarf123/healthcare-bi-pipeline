# Healthcare BI Pipeline: Claims ETL & Star-Schema Warehouse

**End-to-end business intelligence workflow — from messy source extracts to a dimensional warehouse and executive KPIs.**

![Denial rate trend](docs/denial_rate_trend.png)

## Overview

Revenue-cycle leaders ask the same questions every month: *what's our denial rate, which payers are holding dollars, and where is volume coming from?* Answering them reliably requires more than queries — it requires a modeled warehouse where every report agrees on the numbers.

This project implements that full BI workflow on synthetic healthcare claims data:

1. **Extract** — three raw source files (claims, encounters, providers) simulating real payer/EHR extracts, complete with realistic quality problems: duplicate claims, inconsistent status casing, missing payer values
2. **Transform** — data-quality rules plus dimensional modeling into a Kimball-style star schema (`fact_claims` + 4 dimensions)
3. **Load** — SQLite warehouse plus CSV exports of every table so the model is browsable right here on GitHub
4. **Analyze & Share** — five stakeholder KPI queries and an auto-generated denial-rate trend chart

> All data is synthetic and reproducible (seeded RNG). No PHI anywhere in this repository.

## Why this design

I built the schema around the questions the business actually asks, not around the source files. Denied claims stay in the fact table as first-class rows with an `is_denied` flag — because denial analysis *is* the use case, and pre-computing the flag means every analyst's denial rate matches. Full rationale in [docs/data_model.md](docs/data_model.md), including the ER diagram.

My background supporting insurance systems shaped the data-quality rules: duplicate claim submissions and payer-name gaps aren't hypothetical — they're what real extracts look like.

## Architecture

```mermaid
flowchart LR
  R1["claims_raw.csv"] --> ETL
  R2["encounters_raw.csv"] --> ETL
  R3["providers_raw.csv"] --> ETL
  ETL["run_etl.py<br/>extract - clean - conform"] --> DQ{"Data-quality rules"}
  DQ -->|rejected| QUAR["Quarantined rows<br/>(counted, not silently dropped)"]
  DQ -->|passed| STAR
  STAR["Star schema"] --> F["fact_claims"]
  STAR --> D1["dim_payer"]
  STAR --> D2["dim_provider"]
  STAR --> D3["dim_diagnosis"]
  STAR --> D4["dim_date"]
  F --> KPI["kpi_queries.sql<br/>revenue-cycle KPIs"]
  D1 --> KPI
  D2 --> KPI
  D3 --> KPI
  D4 --> KPI
  KPI --> VIZ["build_dashboard_chart.py<br/>denial-rate trend"]
```

The star schema is the point of the project. Loading claims into one wide table would
answer a single question; conforming them into a fact table with shared dimensions lets
the same data answer denial rate by payer, by provider, by diagnosis, and over time
without rewriting the pipeline.

## Data quality and privacy guardrails

- **Synthetic data only.** Claims, encounters, and providers are generated. No real
  patient, provider, or payer data — and no PHI — appears in this repository.
- **No third-party data egress.** The pipeline runs locally against local files. Nothing
  is sent to an external API, warehouse, or cloud service.
- **Rejected rows are counted, never silently dropped.** A pipeline that quietly discards
  malformed records produces confident, wrong dashboards. Rejects are surfaced so the
  numbers downstream can be trusted.
- **Referential integrity enforced at load.** Fact rows that cannot resolve to a dimension
  key are rejected rather than loaded with a null, which keeps joins honest.
- **Deterministic and reproducible.** Source generation is seeded, so a KPI that changes
  reflects a logic change rather than new random data.
- **Minimum necessary.** The warehouse carries only the fields the KPIs require; it does
  not hoard columns "in case we need them later."

## Repository structure

```
healthcare-bi-pipeline/
├── data/raw/            # Source extracts (generated, intentionally messy)
├── etl/
│   ├── generate_source_data.py   # Seeded synthetic source data
│   ├── run_etl.py                # Extract → Transform → Load
│   └── build_dashboard_chart.py  # KPI chart for reporting
├── warehouse/           # Loaded star schema (CSV per table + SQLite)
├── sql/kpi_queries.sql  # 5 business KPI queries with commentary
└── docs/data_model.md   # ER diagram + design decisions
```

## Key results (from the loaded warehouse)

Monthly denial rates range from roughly 5% to 19% across 2025, with **Medicare holding the largest dollars-at-risk (~$1,400 denied of ~$11,400 billed)**. "Non-covered service" is the costliest denial reason. Every number is reproducible by running the pipeline.

## How to run

```bash
pip install pandas matplotlib
python etl/generate_source_data.py   # create raw source extracts
python etl/run_etl.py                # build the warehouse
python etl/build_dashboard_chart.py  # generate the KPI chart
```

Then run any query from `sql/kpi_queries.sql` against `warehouse/healthcare_dw.db`.

## Skills demonstrated

ETL design (extract/transform/load separation) · dimensional modeling (star schema, surrogate keys, date dimension) · data-quality engineering (dedup, conforming, null handling) · KPI development for revenue-cycle stakeholders · Python (pandas) · SQL · SQLite

## About

Part of my healthcare analytics portfolio — built to apply the Google Business Intelligence certificate to the insurance-billing domain I know from years of healthcare IT support.

📫 elazarferrer1@gmail.com · [Profile](https://github.com/elazarf123)
