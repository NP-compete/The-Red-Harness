<!-- expensemaster · from 09-golden-query-templates-gl-onestream-2.md -->
### 7.5 Who are the top vendors by total spend?

```sql
-- Top vendors by total spend
SELECT
    vendor_customer,
    SUM(amount_usd) as total_usd
FROM EXPENSEMASTER_DB.RHAI_MARTS.GL_SUB_LEDGER_AGGREGATE
WHERE YEAR(period_date) = YEAR(CURRENT_DATE())
  AND vendor_customer IS NOT NULL
GROUP BY vendor_customer
ORDER BY total_usd DESC
LIMIT 10;
```

**Variation - Top vendors with category breakdown:**

```sql
SELECT
    vendor_customer,
    account_rollup as expense_category,
    SUM(amount_usd) as total_usd
FROM EXPENSEMASTER_DB.RHAI_MARTS.GL_SUB_LEDGER_AGGREGATE
WHERE YEAR(period_date) = YEAR(CURRENT_DATE())
  AND vendor_customer IS NOT NULL
GROUP BY vendor_customer, account_rollup
ORDER BY total_usd DESC
LIMIT 20;
```

**Variation - Top N vendors with prior year comparison:**
When the user asks for "top N vendors" **and** "compare to the year prior" / "how do they compare to last year", return **one query** that includes **both** years and comparison columns. Do not return only the current year.

**Amount column:** If the user's query contains **"using the current plan rate"**, **"use the current plan rate"**, **"current plan rate"**, **"at current plan rate"**, or **"current year plan rate"**, use **`amount_usd_current_plan_year`** in every SUM(CASE...) and in the HAVING clause. Otherwise use **`amount_usd`**. Always end `_filter_note` with **"(amounts at current year plan rate)"** when using `amount_usd_current_plan_year`, or **"(amounts at plan rate at time of transaction)"** when using `amount_usd`.

- Filter `period_date` to span **both** years (e.g. `>= '2024-01-01' AND < '2026-01-01'` for CY24 vs CY25).
- Use conditional `SUM(CASE WHEN period_date in current year THEN amount_usd ELSE 0 END)` (or `amount_usd_current_plan_year` when the user asked for current plan rate—see trigger phrases above).
- Include columns: current year spend, prior year spend, absolute change, and YoY % change (with `NULLIF` to avoid division by zero).
- Order by **current year** spend DESC and apply LIMIT N so "top N" is by current year; comparison columns show how each of those top N compared to prior year.

```sql
-- Example A: Default (amount_usd). Use this when the user does NOT say "using the current plan rate" (or similar).
SELECT
    'Filtered by: ... (amounts at plan rate at time of transaction)' AS _filter_note,
    vendor_customer,
    SUM(CASE WHEN period_date >= '2025-01-01' AND period_date < '2026-01-01' THEN amount_usd ELSE 0 END) AS cy25_spend,
    SUM(CASE WHEN period_date >= '2024-01-01' AND period_date < '2025-01-01' THEN amount_usd ELSE 0 END) AS cy24_spend,
    ...
FROM EXPENSEMASTER_DB.RHAI_MARTS.GL_SUB_LEDGER_AGGREGATE
WHERE ...
HAVING SUM(CASE WHEN period_date >= '2025-01-01' AND period_date < '2026-01-01' THEN amount_usd ELSE 0 END) > 0
ORDER BY cy25_spend DESC LIMIT 5;
```

```sql
-- Example B: User said "using the current plan rate" (or "current plan rate" / "current year plan rate"). Use amount_usd_current_plan_year everywhere.
SELECT
    'Filtered by: ... (amounts at current year plan rate)' AS _filter_note,
    vendor_customer,
    SUM(CASE WHEN period_date >= '2025-01-01' AND period_date < '2026-01-01' THEN amount_usd_current_plan_year ELSE 0 END) AS cy25_spend,
    SUM(CASE WHEN period_date >= '2024-01-01' AND period_date < '2025-01-01' THEN amount_usd_current_plan_year ELSE 0 END) AS cy24_spend,
    SUM(CASE WHEN period_date >= '2025-01-01' AND period_date < '2026-01-01' THEN amount_usd_current_plan_year ELSE 0 END)
      - SUM(CASE WHEN period_date >= '2024-01-01' AND period_date < '2025-01-01' THEN amount_usd_current_plan_year ELSE 0 END) AS spend_change,
    ROUND(
        (SUM(CASE WHEN period_date >= '2025-01-01' AND period_date < '2026-01-01' THEN amount_usd_current_plan_year ELSE 0 END)
         - SUM(CASE WHEN period_date >= '2024-01-01' AND period_date < '2025-01-01' THEN amount_usd_current_plan_year ELSE 0 END))
        / NULLIF(SUM(CASE WHEN period_date >= '2024-01-01' AND period_date < '2025-01-01' THEN amount_usd_current_plan_year ELSE 0 END), 0) * 100,
    2) AS yoy_growth_pct
FROM EXPENSEMASTER_DB.RHAI_MARTS.GL_SUB_LEDGER_AGGREGATE
WHERE (cost_center_department = 'IT'
       OR REGEXP_LIKE(cost_center_hierarchy, '(^|.*[|])IT[_|].*'))
  AND period_date >= '2024-01-01' AND period_date < '2026-01-01'
  AND vendor_customer IS NOT NULL
GROUP BY vendor_customer
HAVING SUM(CASE WHEN period_date >= '2025-01-01' AND period_date < '2026-01-01' THEN amount_usd_current_plan_year ELSE 0 END) > 0
ORDER BY cy25_spend DESC
LIMIT 5;
```
- Order by current-year spend; in Snowflake you can reference the alias `cy25_spend` in ORDER BY.
