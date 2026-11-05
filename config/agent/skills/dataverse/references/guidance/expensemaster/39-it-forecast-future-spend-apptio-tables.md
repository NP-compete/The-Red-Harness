<!-- expensemaster · from 10-it-forecast-future-spend-apptio-tables-1.md -->
## IT forecast / future spend (Apptio tables)

**Snowflake schema:** Qualify all ITPF and TBM objects as **`EXPENSEMASTER_DB.RHAI_MARTS.<table>`**.

**Use for:** **IT-only** **forecast and planning** — future spend, forecast versions, PO/contract/labor/asset lines in the planning tool, spend-driver / project forecast lines, and **application or service TCO** (ITPF + TBM marts). Built from **financial/GL inputs** plus Apptio planning and allocation. **Routing:** **Do not** use this section as the default for *"What did IT spend?"* **actuals** questions (past or closed periods); answer those with **`GL_SUB_LEDGER_AGGREGATE`** (and **OneStream** `scenario = 'Actual'` when FP&A roll-up is required). ITPF rows with `period_date < CURRENT_DATE()` exist for planning workflows, but **stakeholder questions about booked IT spend** still default to **GL/OneStream**. **Not for:** company-wide budget variance, headcount, non-IT, or lease → **GL/OneStream**. **Rules:** [Critical rules](#-critical-rules) → Apptio.

**Where to find what:** **README** (this section) = product-level rules (period_date, C&B, scope, TBM concepts, join patterns, query templates). **dbt mart YAML** = per-table routing (USE THIS TABLE WHEN / DO NOT USE WHEN) and table-specific CRITICAL SQL (version filter, snapshot_date, SUM(cost), etc.). Use both: README to choose Apptio and apply shared rules; YAML to pick the table and apply its filters.

**Which table:** dbt mart descriptions → ITPF_* (e.g. vendor → ITPF_FORECAST_DAILY_CURRENT; PO → ITPF_CONTRACT_FORECAST_W_DELEGATION; labor → ITPF_LABOR_FORECAST_DAILY) or APP_* / SERVICE_* for app/service TCO. Mart YAML: `apptio-dbt/models/marts/` or `expensemaster-dbt/models/rhai_marts/` (depending on deployment).
