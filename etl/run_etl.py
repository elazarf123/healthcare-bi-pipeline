"""
run_etl.py
Extract -> Transform -> Load pipeline.

Extract:   reads the raw source extracts (claims, encounters, providers)
Transform: cleans and conforms the data, then models it as a star schema
Load:      writes the warehouse to SQLite AND exports each table to CSV
           (warehouse/ folder) so the model is browsable on GitHub

Star schema:
    fact_claims ── dim_encounter, dim_provider, dim_payer, dim_diagnosis, dim_date

Run:  python etl/run_etl.py   (after etl/generate_source_data.py)
"""

import sqlite3
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent.parent
RAW = BASE / "data" / "raw"
WAREHOUSE = BASE / "warehouse"
WAREHOUSE.mkdir(exist_ok=True)
DB_PATH = WAREHOUSE / "healthcare_dw.db"


# ---------------------------------------------------------------- EXTRACT
def extract() -> dict[str, pd.DataFrame]:
    frames = {
        "claims": pd.read_csv(RAW / "claims_raw.csv"),
        "encounters": pd.read_csv(RAW / "encounters_raw.csv"),
        "providers": pd.read_csv(RAW / "providers_raw.csv"),
    }
    for name, df in frames.items():
        print(f"  extracted {name}: {len(df)} rows")
    return frames


# -------------------------------------------------------------- TRANSFORM
def transform(frames: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    claims = frames["claims"].copy()
    encounters = frames["encounters"].copy()
    providers = frames["providers"].copy()

    # -- Data quality fixes on the claims extract --------------------------
    before = len(claims)
    claims = claims.drop_duplicates(subset="claim_id", keep="first")
    print(f"  deduplicated claims: removed {before - len(claims)} rows")

    claims["claim_status"] = claims["claim_status"].str.strip().str.title()   # paid/PAID -> Paid
    claims["payer"] = claims["payer"].fillna("Unknown").replace("", "Unknown")
    claims["billed_amount"] = pd.to_numeric(claims["billed_amount"], errors="coerce").fillna(0.0)
    claims["denial_reason"] = claims["denial_reason"].fillna("")

    # -- Dimensions ---------------------------------------------------------
    dim_provider = providers.rename(columns={"provider_id": "provider_key"})

    dim_payer = (
        claims[["payer"]].drop_duplicates().reset_index(drop=True)
        .rename_axis("payer_key").reset_index()
    )
    dim_payer["payer_key"] += 1

    dim_diagnosis = (
        encounters[["diagnosis_code", "diagnosis_desc"]]
        .drop_duplicates().reset_index(drop=True)
    )

    dates = pd.to_datetime(encounters["visit_date"]).drop_duplicates().sort_values()
    dim_date = pd.DataFrame({
        "date_key": dates.dt.strftime("%Y%m%d").astype(int),
        "full_date": dates.dt.date.astype(str),
        "year": dates.dt.year,
        "quarter": dates.dt.quarter,
        "month": dates.dt.month,
        "month_name": dates.dt.month_name(),
        "day_of_week": dates.dt.day_name(),
    }).reset_index(drop=True)

    # -- Fact table -----------------------------------------------------------
    fact = claims.merge(encounters, on="encounter_id", how="inner")
    fact = fact.merge(dim_payer, on="payer", how="left")
    fact["date_key"] = pd.to_datetime(fact["visit_date"]).dt.strftime("%Y%m%d").astype(int)
    fact["is_denied"] = (fact["claim_status"] == "Denied").astype(int)

    fact_claims = fact[[
        "claim_id", "encounter_id", "patient_id", "provider_id", "payer_key",
        "diagnosis_code", "cpt_code", "date_key",
        "billed_amount", "claim_status", "is_denied", "denial_reason",
    ]].rename(columns={"provider_id": "provider_key"})

    print(f"  fact_claims: {len(fact_claims)} rows; dims: "
          f"{len(dim_provider)} providers, {len(dim_payer)} payers, "
          f"{len(dim_diagnosis)} diagnoses, {len(dim_date)} dates")

    return {
        "fact_claims": fact_claims,
        "dim_provider": dim_provider,
        "dim_payer": dim_payer,
        "dim_diagnosis": dim_diagnosis,
        "dim_date": dim_date,
    }


# ------------------------------------------------------------------- LOAD
def load(tables: dict[str, pd.DataFrame]) -> None:
    con = sqlite3.connect(DB_PATH)
    for name, df in tables.items():
        df.to_sql(name, con, if_exists="replace", index=False)
        df.to_csv(WAREHOUSE / f"{name}.csv", index=False)
        print(f"  loaded {name} -> SQLite + {name}.csv")
    con.close()


if __name__ == "__main__":
    print("EXTRACT")
    frames = extract()
    print("TRANSFORM")
    tables = transform(frames)
    print("LOAD")
    load(tables)
    print(f"Done. Warehouse at {DB_PATH}")
