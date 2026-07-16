/* =============================================================
   kpi_queries.sql
   Business-facing KPI queries against the star schema.
   Run against warehouse/healthcare_dw.db (SQLite).
   ============================================================= */

-- KPI 1: Monthly denial rate trend
-- The revenue-cycle team's headline metric. Joins fact to dim_date
-- so the grain is calendar month regardless of claim volume.
SELECT
    d.year,
    d.month,
    d.month_name,
    COUNT(*)                                    AS total_claims,
    SUM(f.is_denied)                            AS denied_claims,
    ROUND(100.0 * SUM(f.is_denied) / COUNT(*), 1) AS denial_rate_pct
FROM fact_claims f
JOIN dim_date d ON d.date_key = f.date_key
GROUP BY d.year, d.month, d.month_name
ORDER BY d.year, d.month;

-- KPI 2: Revenue and denial exposure by payer
SELECT
    p.payer,
    COUNT(*)                                    AS claims,
    ROUND(SUM(f.billed_amount), 2)              AS total_billed,
    ROUND(SUM(CASE WHEN f.is_denied = 1 THEN f.billed_amount ELSE 0 END), 2)
                                                AS dollars_at_risk,
    ROUND(100.0 * SUM(f.is_denied) / COUNT(*), 1) AS denial_rate_pct
FROM fact_claims f
JOIN dim_payer p ON p.payer_key = f.payer_key
GROUP BY p.payer
ORDER BY dollars_at_risk DESC;

-- KPI 3: Average billed amount by provider specialty
SELECT
    pr.specialty,
    COUNT(*)                                    AS claims,
    ROUND(AVG(f.billed_amount), 2)              AS avg_billed,
    ROUND(SUM(f.billed_amount), 2)              AS total_billed
FROM fact_claims f
JOIN dim_provider pr ON pr.provider_key = f.provider_key
GROUP BY pr.specialty
ORDER BY total_billed DESC;

-- KPI 4: Top denial reasons with financial impact
SELECT
    f.denial_reason,
    COUNT(*)                                    AS denied_claims,
    ROUND(SUM(f.billed_amount), 2)              AS dollars_denied
FROM fact_claims f
WHERE f.is_denied = 1
GROUP BY f.denial_reason
ORDER BY dollars_denied DESC;

-- KPI 5: Claim volume by diagnosis (top conditions driving utilization)
SELECT
    dx.diagnosis_code,
    dx.diagnosis_desc,
    COUNT(*)                                    AS claims,
    ROUND(SUM(f.billed_amount), 2)              AS total_billed
FROM fact_claims f
JOIN dim_diagnosis dx ON dx.diagnosis_code = f.diagnosis_code
GROUP BY dx.diagnosis_code, dx.diagnosis_desc
ORDER BY claims DESC;
