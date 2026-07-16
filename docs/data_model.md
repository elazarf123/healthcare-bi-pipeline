# Data Model — Healthcare Claims Star Schema

The warehouse uses a classic Kimball-style star schema: one fact table at the
claim grain, surrounded by conformed dimensions.

```mermaid
erDiagram
    FACT_CLAIMS }o--|| DIM_PROVIDER : provider_key
    FACT_CLAIMS }o--|| DIM_PAYER : payer_key
    FACT_CLAIMS }o--|| DIM_DIAGNOSIS : diagnosis_code
    FACT_CLAIMS }o--|| DIM_DATE : date_key

    FACT_CLAIMS {
        string claim_id PK
        string encounter_id
        string patient_id
        string provider_key FK
        int payer_key FK
        string diagnosis_code FK
        string cpt_code
        int date_key FK
        decimal billed_amount
        string claim_status
        int is_denied
        string denial_reason
    }
    DIM_PROVIDER {
        string provider_key PK
        string provider_name
        string specialty
    }
    DIM_PAYER {
        int payer_key PK
        string payer
    }
    DIM_DIAGNOSIS {
        string diagnosis_code PK
        string diagnosis_desc
    }
    DIM_DATE {
        int date_key PK
        date full_date
        int year
        int quarter
        int month
        string month_name
        string day_of_week
    }
```

## Design decisions

**Grain.** One row per claim. Denials are kept as rows (with `is_denied` flag
and `denial_reason`) rather than filtered out — denial analysis is a primary
use case, so denied claims are first-class facts.

**`is_denied` as a fact flag.** Pre-computing the binary flag keeps KPI SQL
simple (`SUM(is_denied)/COUNT(*)`) and consistent across every report instead
of each analyst re-deriving it from `claim_status` strings.

**Date dimension with integer key (YYYYMMDD).** Standard warehouse pattern:
compact joins, human-readable keys, and month/quarter/day-of-week attributes
available without date functions in every query.

**Payer surrogate key.** Payer names arrive dirty from the source (missing
values ~3%). Conforming them once into `dim_payer` (with an `Unknown` member)
means every downstream report treats payers identically.

## Data quality rules applied in Transform

| Rule | Source issue | Handling |
|---|---|---|
| Deduplicate on `claim_id` | Duplicate claim submissions | Keep first occurrence |
| Standardize `claim_status` | `paid` / `Paid` / `PAID` | Title-case normalization |
| Missing payer | Blank strings in extract | Mapped to `Unknown` payer member |
| Amount validation | Text-typed amounts | Coerced to numeric; invalid → 0.00 |
