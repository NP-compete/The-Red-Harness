<!-- expensemaster · from 03-transparency-columns.md -->
## 🔍 Transparency Columns

Every query includes transparency columns for data lineage:

- `_filter_note` — **First column** in the SELECT list. **GL/OneStream:** see Critical Rule #7 (filters + plan-rate suffix). **Apptio spend:** see Critical Rule Apptio #8 (fixed disclosure string only). **Cloudability mart:** see Critical rules → **Cloudability** (filter summary + **`SUM(period_amount)`** disclosure; not GL plan-rate).
- `matched_at` — Shows which column matched and the exact value (row-level); use where helpful (GL/OneStream patterns); optional on high-level Apptio aggregates when not row-level matching; optional on **`CLOUDABILITY_COST_INFO`** aggregates.
