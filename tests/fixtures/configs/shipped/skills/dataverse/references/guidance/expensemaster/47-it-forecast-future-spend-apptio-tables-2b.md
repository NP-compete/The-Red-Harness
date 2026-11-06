<!-- expensemaster · from 11-it-forecast-future-spend-apptio-tables-2.md -->
#### 8.4b Financial impact of not renewing IT contracts (forecast savings by year)

**Canonical question**: What is the financial impact of not renewing IT contracts ending in 2028?

**Use the same template for any closely related ask** — as long as the user means **forecast dollars tied to renewing past the contractual end** in the IT contract mart (not GL actuals, not ad‑hoc PO termination mid‑term). Examples of equivalent intent: *financial impact if we do not renew / let expire / non‑renew*; *cost avoidance* or *savings* from **not extending** contracts that **end in calendar year Y** (or a stated fiscal window); *how much forecast spend goes away* if we **drop the renewal tail** for IT contracts maturing in **Y**; *by vendor / PO / cost center* for that same non‑renewal definition. **Always** keep the **same core filters** below; only **parameterize** end year (or **`contract_end_date` range**), optional dimensions, and whether the answer is **by `YEAR(period_date)`** or **one grand total**.

**Do not use this template for**: **immediate PO termination** or “stop this PO now” before natural end — use [§8.4](#84-po-termination-impact-analysis) / [§8.7](#87-po-spend-analysis-annual-future-cost-by-year) (`ITPF_CONTRACT_FORECAST_W_DELEGATION` with `po_number` and forward `period_date`, different business rule). **Booked** savings belong in **GL**, not this mart.

**Table**: `ITPF_CONTRACT_FORECAST_W_DELEGATION` only (`EXPENSEMASTER_DB.RHAI_MARTS`).

**Column names on `EXPENSEMASTER_DB.RHAI_MARTS`:** contractual end date is **`contract_end_date`**. Also common on this mart: **`vendor_name`**, **`cost_center_code`**, **`po_number`**. Use **`DESCRIBE TABLE EXPENSEMASTER_DB.RHAI_MARTS.ITPF_CONTRACT_FORECAST_W_DELEGATION`** if a column is missing from generated SQL.

**Definition (fixed rule)**: **Forecast savings / non‑renewal impact** = **`SUM(period_amount)`** where:

1. **`extend = TRUE`** — plan assumes spend **after** contractual end (renewal modeled).
2. **`period_date > contract_end_date`** — **post–end-date renewal tail** only, not in‑term amortization.
3. **Contract cohort** — default **`YEAR(contract_end_date::DATE) = <Y>`** for calendar year **Y**; use a **`contract_end_date` date range** if the user means fiscal year.
4. **Latest plan** — CTE **`base`** adds **`forecast_entry_month`** from **`current_fy_plan_version`** using the **same** `DATE_FROM_PARTS` / `REGEXP_SUBSTR` pattern as **`ITPF_FORECAST_DAILY_CURRENT`**; then **`forecast_entry_month = (SELECT MAX(forecast_entry_month) FROM base)`**.

State clearly in the answer: amounts are **Apptio forecast** for the **modeled renewal tail**, not guaranteed cash or GL.

**Adaptations from the question**:

- Replace **`2028`** with the user’s **end year** (or use a **`contract_end_date` range**).
- **Single number**: drop **`YEAR(b.period_date)`** from `SELECT`/`GROUP BY`; keep **`SUM(b.period_amount)`**.
- **Breakdown** (`RHAI_MARTS`): add **`vendor_name`**, **`po_number`**, **`contract_type`**, **`cost_center_code`**, **`department`** to `SELECT`/`GROUP BY` as needed.
- **OpEx vs CapEx**: add **`account_expense_type`** to `SELECT`/`GROUP BY` or filter.

**`extend` type**: If `extend` is not boolean, use e.g. `UPPER(TRIM(extend::VARCHAR)) IN ('TRUE', 'T', '1', 'YES')`.

```sql
-- Parameter: calendar year of contract end (e.g. 2028). RHAI_MARTS uses contract_end_date (not end_date).
WITH base AS (
    SELECT
        c.*,
        DATE_FROM_PARTS(
            2000 + CAST(REGEXP_SUBSTR(c.current_fy_plan_version, 'CY([0-9]{2})', 1, 1, 'e', 1) AS INTEGER),
            CAST(REGEXP_SUBSTR(c.current_fy_plan_version, '\\(([0-9]{2})x', 1, 1, 'e', 1) AS INTEGER) + 1,
            1
        ) AS forecast_entry_month
    FROM EXPENSEMASTER_DB.RHAI_MARTS.ITPF_CONTRACT_FORECAST_W_DELEGATION AS c
)
SELECT
    MAX('Using Apptio data, which includes spend that resides in IT cost centers.') AS _filter_note,
    YEAR(b.period_date) AS year,
    SUM(b.period_amount) AS total_savings
FROM base AS b
WHERE b.forecast_entry_month = (SELECT MAX(forecast_entry_month) FROM base)
  AND YEAR(b.contract_end_date::DATE) = 2028
  AND b.extend = TRUE
  AND b.period_date > b.contract_end_date
GROUP BY YEAR(b.period_date)
ORDER BY year;
```

For a **single total** (no year breakdown), omit **`YEAR(b.period_date)`** from the **`SELECT`**/**`GROUP BY`** and use **`SUM(b.period_amount) AS total_savings`** only.
