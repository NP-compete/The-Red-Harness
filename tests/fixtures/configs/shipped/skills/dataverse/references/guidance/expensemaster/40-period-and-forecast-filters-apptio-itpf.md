<!-- expensemaster · from 10-it-forecast-future-spend-apptio-tables-1.md -->
### Period and forecast filters (Apptio/ITPF)

ITPF tables have `period_date` (DATE) and `forecast_entry_month` (DATE) columns. **Always use these instead of parsing text columns.**

```sql
-- ✅ CORRECT: Use period_date for filtering
WHERE period_date = '2025-06-01'                              -- June 2025
WHERE period_date BETWEEN '2025-01-01' AND '2025-12-01'       -- FY2025
WHERE period_date >= DATE_TRUNC('month', CURRENT_DATE())      -- Future only
WHERE period_date < CURRENT_DATE()                            -- Actuals (past)

-- ❌ INCORRECT: Don't parse period text
WHERE PERIOD = 'P6 FY2025'
```

**Latest forecast filter:** ITPF tables require a version filter so you get one plan version; which column and expression depend on the table. **Contract** uses `current_fy_plan_version`; **all other ITPF** (forecast daily, labor, asset, variance) use `forecast_entry_month`. **`APP_SPEND_*`** and **`SERVICE_COST_*`** do **not** use a forecast filter. For each table’s exact filter and rules, use the dbt mart YAML (CRITICAL section).
