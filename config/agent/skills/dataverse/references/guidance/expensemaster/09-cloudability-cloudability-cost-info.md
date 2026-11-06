<!-- expensemaster · from 02-critical-rules.md -->
### Cloudability (`CLOUDABILITY_COST_INFO`)

1. **Database & schema**: **`EXPENSEMASTER_DB.RHAI_MARTS.CLOUDABILITY_COST_INFO`** (dbt `expensemaster-dbt`, `models/rhai_marts/`).
2. **Money column**: Always **`SUM(period_amount)`** for dollars.
3. **Dates**: Filter on **`period_date`** (DATE).
4. **`_filter_note`**: Put **`_filter_note` in the first column**. Summarize the active **`period_date`** / **`vendor`** / **`cost_center_code`** / **`account_name`** (etc.) filters, and end with that amounts are **`SUM(period_amount)`** from **`EXPENSEMASTER_DB.RHAI_MARTS.CLOUDABILITY_COST_INFO`**. On grouped queries, use **`MAX('<your note>') AS _filter_note`** when the note is a literal. **`matched_at`** is optional for this mart.
5. **Scope**: **Cloudability-reported cloud charges only** — not **all** company spend with Amazon/Azure/GCP/IBM; for that use **`GL_SUB_LEDGER_AGGREGATE`** and explain the difference.
6. **Department on cloud**: **`cost_center_department`** and **`cost_center_hierarchy`** (OneStream-enriched) for org/department questions (e.g. “Sales department cloud spend”); use the same known-department names where they apply (e.g. **`'Sales'`**).
7. **Hierarchy REGEXP Word-Boundary Matching**: The `cost_center_hierarchy` column uses `|` as segment delimiter and `_` as word separator. **Never use bare `ILIKE '%<term>%'`** — it matches substrings (e.g., `%IT%` matches Benef**it**s). Use **REGEXP** for true word-boundary matching: `REGEXP_LIKE(cost_center_hierarchy, '(^|.*[|])' || '<term>' || '[_|].*')`. See [Hierarchy Matching Rule](#-critical-hierarchy-matching-rule-avoid-false-positives) section.
8. **Coverage**: **Not all cloud spend is in Cloudability** — a **few GCP billing accounts** and an **AWS FedRamp payer account** are **not** monitored; say so when answering from this mart.
9. **AWS spikes**: When **`vendor`** is **Amazon** or the user asks about AWS trends/anomalies, large spikes may be **Marketplace** purchases or **upfront Reservations** — detail is in the **Cloudability** product.
10. **Answer prose**: After presenting results, also state applicable scope, timing, and traps from **`expensemaster-dbt/docs/cloudability_cost_info.md`** (sections **A**, **C**, **D**, **Point-in-time**) in the response — not only in **`_filter_note`**.
