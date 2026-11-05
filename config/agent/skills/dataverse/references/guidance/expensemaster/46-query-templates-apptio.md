<!-- expensemaster · from 10-it-forecast-future-spend-apptio-tables-1.md -->
### Query templates (Apptio)

**`_filter_note`:** use **`'Using Apptio data, which includes spend that resides in IT cost centers.'`** as the first selected column (Critical Rule Apptio #8). If the query has **`GROUP BY`**, use **`MAX('Using Apptio data, which includes spend that resides in IT cost centers.') AS _filter_note`**.
- When ordering by a metric in descending order (example: `ORDER BY SUM(period_amount) DESC`), always put nulls last — see [§8.1 Ranking Vendors by Spend Analysis](#81-ranking-vendors-by-spend-analysis) for an example query.
- Whenever giving a metric value(sum,average, etc...), even if asked for a yearly amount, always show the breakdown by month(using period_date or month_date depending on table used) as well.

#### 8.1 Ranking Vendors by Spend Analysis

**Question**: What are the top IT Red Hat vendors by spend next month?

```sql
select
period_date,
vendor,
expense_type,
sum(period_amount)
from EXPENSEMASTER_DB.RHAI_MARTS.ITPF_FORECAST_DAILY_CURRENT
where forecast_entry_month = (select max(f.forecast_entry_month) from EXPENSEMASTER_DB.RHAI_MARTS.ITPF_FORECAST_DAILY_CURRENT f)
and period_date = DATE_TRUNC('month', DATEADD(month, 1, CURRENT_DATE()))
and vendor is not null
group by period_date,vendor, expense_type
order by sum(period_amount) desc nulls last;
```

#### 8.2 Cost Center Variance Analysis

**Question**: What is the cost difference for CC860 between Oct 2025 and Oct 2026?

```sql
WITH cost_breakdown AS (
  SELECT
    period_date,
    COST_POOL,
    SUM(PERIOD_AMOUNT) as total_amount
  FROM EXPENSEMASTER_DB.RHAI_MARTS.ITPF_FORECAST_DAILY_CURRENT
  WHERE COST_CENTER = '860'
    AND period_date IN ('2025-10-01', '2026-10-01')
    AND forecast_entry_month = (SELECT MAX(forecast_entry_month) FROM EXPENSEMASTER_DB.RHAI_MARTS.ITPF_FORECAST_DAILY_CURRENT)
  GROUP BY period_date, COST_POOL
)
SELECT
  MAX('Using Apptio data, which includes spend that resides in IT cost centers.') AS _filter_note,
  COST_POOL,
  SUM(CASE WHEN period_date = '2025-10-01' THEN total_amount ELSE 0 END) as oct_2025,
  SUM(CASE WHEN period_date = '2026-10-01' THEN total_amount ELSE 0 END) as oct_2026,
  SUM(CASE WHEN period_date = '2026-10-01' THEN total_amount ELSE 0 END)
    - SUM(CASE WHEN period_date = '2025-10-01' THEN total_amount ELSE 0 END) as variance
FROM cost_breakdown
GROUP BY COST_POOL
ORDER BY ABS(variance) DESC nulls last;
```

> **Note**: C&B (Labor costs) are NOT forecasted in future years. If comparing current to future years, exclude C&B for accurate comparison or note the limitation.

#### 8.3 Future Costs Analysis

**Question**: What are the future costs for Dell?

> **CRITICAL**: Use `period_date` for date filtering — do not parse `period` text.

```sql
SELECT
    MAX('Using Apptio data, which includes spend that resides in IT cost centers.') AS _filter_note,
    period_date,
    period,
    SUM(PERIOD_AMOUNT) / 1000000 AS dell_forecast_millions
FROM EXPENSEMASTER_DB.RHAI_MARTS.ITPF_FORECAST_DAILY_CURRENT
WHERE VENDOR ILIKE '%Dell%'
  AND forecast_entry_month = (SELECT MAX(forecast_entry_month) FROM EXPENSEMASTER_DB.RHAI_MARTS.ITPF_FORECAST_DAILY_CURRENT)
  AND period_date >= DATE_TRUNC('month', CURRENT_DATE())
GROUP BY period_date, period
ORDER BY period_date;
```

#### 8.4 PO Termination Impact Analysis

**Q
