<!-- expensemaster · from 11-it-forecast-future-spend-apptio-tables-2.md -->
#### 8.7 PO spend analysis (annual future cost by year)

**Question**: What would be the effect of terminating PO 1010108994 immediately? (Annual future cost by year.)

```sql
SELECT
    MAX('Using Apptio data, which includes spend that resides in IT cost centers.') AS _filter_note,
    YEAR(period_date) AS year,
    SUM(PERIOD_AMOUNT) AS total_annual_cost
FROM EXPENSEMASTER_DB.RHAI_MARTS.ITPF_CONTRACT_FORECAST_W_DELEGATION
WHERE po_number = '1010108994'
  AND current_fy_plan_version = (SELECT MAX(current_fy_plan_version) FROM EXPENSEMASTER_DB.RHAI_MARTS.ITPF_CONTRACT_FORECAST_W_DELEGATION)
  AND period_date >= DATE_TRUNC('month', CURRENT_DATE())
GROUP BY YEAR(period_date)
ORDER BY year;
```
