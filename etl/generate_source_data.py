"""
generate_source_data.py
Creates the fictitious source-system extracts that feed the ETL pipeline.

Simulates two upstream systems a BI team typically receives:
  - claims_raw.csv     : payer claims extract (messy — mixed casing, nulls)
  - encounters_raw.csv : EHR encounter extract

Seeded RNG so the dataset is reproducible. No PHI — all data is synthetic.
"""

import csv
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(42)

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

SPECIALTIES = ["Family Medicine", "Cardiology", "Pulmonology", "Orthopedics", "Endocrinology"]
PAYERS = ["BlueShield PPO", "Medicare", "Medicaid", "Aetna HMO", "UnitedHealth EPO"]
DIAGNOSES = [
    ("E11.9", "Type 2 diabetes mellitus without complications"),
    ("I10", "Essential (primary) hypertension"),
    ("J45.30", "Mild persistent asthma, uncomplicated"),
    ("M54.50", "Low back pain, unspecified"),
    ("E78.5", "Hyperlipidemia, unspecified"),
    ("J06.9", "Acute upper respiratory infection"),
]
CPT = [("99213", 145.00), ("99214", 185.00), ("99215", 245.00), ("94010", 210.00), ("93000", 95.00)]
DENIAL_REASONS = ["", "Coding mismatch", "Missing prior authorization", "Non-covered service", "Duplicate claim"]

providers = [(f"PRV-{100+i}", f"Provider {chr(65+i)}", random.choice(SPECIALTIES)) for i in range(8)]
patients = [f"PT-{5000+i}" for i in range(60)]

start = date(2025, 1, 1)

encounters, claims = [], []
for enc_id in range(1, 301):
    visit_date = start + timedelta(days=random.randint(0, 364))
    patient = random.choice(patients)
    prv_id, prv_name, specialty = random.choice(providers)
    dx_code, dx_desc = random.choice(DIAGNOSES)

    # EHR extract row (clean-ish)
    encounters.append({
        "encounter_id": f"ENC-{enc_id:05d}",
        "patient_id": patient,
        "provider_id": prv_id,
        "visit_date": visit_date.isoformat(),
        "diagnosis_code": dx_code,
        "diagnosis_desc": dx_desc,
    })

    # Claims extract row (intentionally messy: casing, nulls, duplicates)
    cpt_code, amount = random.choice(CPT)
    denied = random.random() < 0.12
    status = "DENIED" if denied else random.choice(["paid", "Paid", "PAID"])
    claims.append({
        "claim_id": f"CLM-{enc_id:05d}",
        "encounter_id": f"ENC-{enc_id:05d}",
        "payer": random.choice(PAYERS) if random.random() > 0.03 else "",   # ~3% missing payer
        "cpt_code": cpt_code,
        "billed_amount": f"{amount:.2f}",
        "claim_status": status,
        "denial_reason": random.choice(DENIAL_REASONS[1:]) if denied else "",
        "submitted_date": (visit_date + timedelta(days=random.randint(1, 14))).isoformat(),
    })

# Inject 5 exact duplicate claims — the ETL must deduplicate
claims.extend(random.sample(claims, 5))

with open(RAW_DIR / "encounters_raw.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=encounters[0].keys())
    w.writeheader()
    w.writerows(encounters)

with open(RAW_DIR / "claims_raw.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=claims[0].keys())
    w.writeheader()
    w.writerows(claims)

# Provider reference file
with open(RAW_DIR / "providers_raw.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["provider_id", "provider_name", "specialty"])
    w.writerows(providers)

print(f"Wrote {len(encounters)} encounters, {len(claims)} claims (5 dupes injected), {len(providers)} providers -> {RAW_DIR}")
