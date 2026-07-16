"""
build_dashboard_chart.py
Generates the README dashboard image (docs/denial_rate_trend.png)
from the loaded warehouse — the "Share" step of the BI workflow.

Run after run_etl.py.
"""

import sqlite3
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

BASE = Path(__file__).resolve().parent.parent
DB = BASE / "warehouse" / "healthcare_dw.db"
OUT = BASE / "docs" / "denial_rate_trend.png"

QUERY = """
SELECT d.month, d.month_name,
       COUNT(*) AS total_claims,
       ROUND(100.0 * SUM(f.is_denied) / COUNT(*), 1) AS denial_rate_pct
FROM fact_claims f
JOIN dim_date d ON d.date_key = f.date_key
GROUP BY d.month, d.month_name
ORDER BY d.month;
"""

con = sqlite3.connect(DB)
df = pd.read_sql_query(QUERY, con)
con.close()

fig, ax1 = plt.subplots(figsize=(10, 5))
ax1.bar(df["month_name"].str[:3], df["total_claims"], color="#a5c8e4", label="Claim volume")
ax1.set_ylabel("Claims")
ax2 = ax1.twinx()
ax2.plot(df["month_name"].str[:3], df["denial_rate_pct"], color="#c0392b",
         marker="o", linewidth=2, label="Denial rate %")
ax2.set_ylabel("Denial rate (%)")
ax1.set_title("Claim Volume & Denial Rate by Month — 2025 (synthetic data)")
fig.legend(loc="upper right", bbox_to_anchor=(0.92, 0.92))
fig.tight_layout()
fig.savefig(OUT, dpi=120)
print(f"Saved {OUT}")
