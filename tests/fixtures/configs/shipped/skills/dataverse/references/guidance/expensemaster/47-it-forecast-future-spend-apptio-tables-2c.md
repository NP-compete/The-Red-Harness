<!-- expensemaster · from 11-it-forecast-future-spend-apptio-tables-2.md -->
#### 8.5 Labor/Contractor Cost Analysis

**Question**: What was the labor cost for cost center 850 for the first half of the year?

> **For contractor-specific details**, use `ITPF_LABOR_FORECAST_DAILY` which includes: start/end date, base compensation, employee type, role, vendor (staffing agency).

```sql
SELECT
  MAX('Using Apptio data, which includes spend that resides in IT cost centers.') AS _filter_note,
  cost_center,
  ROUND(SUM(PERIOD_AMOUNT), 2) as total_labor_cost,
  COUNT(DISTINCT line_item_code) as labor_line_items
FROM EXPENSEMASTER_DB.RHAI_MARTS.ITPF_LABOR_FORECAST_DAILY
WHERE COST_CENTER = '850'
  AND period_date BETWEEN '2025-01-01' AND '2025-06-01'
  AND forecast_entry_month = (SELECT MAX(forecast_entry_month) FROM EXPENSEMASTER_DB.RHAI_MARTS.ITPF_LABOR_FORECAST_DAILY)
GROUP BY cost_center;
```

For monthly labor cost use: `(SUM(base_compensation/12))/COUNT(DISTINCT period_date)` — do not use `PERIOD_AMOUNT`.
