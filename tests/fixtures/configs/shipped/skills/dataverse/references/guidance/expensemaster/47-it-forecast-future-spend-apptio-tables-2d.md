<!-- expensemaster · from 11-it-forecast-future-spend-apptio-tables-2.md -->
#### 8.6 Spend Driver Analysis

**Question**: What is the total spend by spend driver?

```sql
SELECT
    MAX('Using Apptio data, which includes spend that resides in IT cost centers.') AS _filter_note,
    SPEND_DRIVER_NAME,
    ROUND(SUM(PERIOD_AMOUNT) / 1000000, 2) AS total_spend_millions,
    ROUND(SUM(CASE WHEN EXPENSE_TYPE = 'OpEx' THEN PERIOD_AMOUNT ELSE 0 END) / 1000000, 2) AS opex_millions,
    ROUND(SUM(CASE WHEN EXPENSE_TYPE = 'CapEx' THEN PERIOD_AMOUNT ELSE 0 END) / 1000000, 2) AS capex_millions
FROM EXPENSEMASTER_DB.RHAI_MARTS.ITPF_FORECAST_DAILY_CURRENT
WHERE SPEND_DRIVER_NAME IS NOT NULL
  AND forecast_entry_month = (SELECT MAX(forecast_entry_month) FROM EXPENSEMASTER_DB.RHAI_MARTS.ITPF_FORECAST_DAILY_CURRENT)
GROUP BY SPEND_DRIVER_NAME
ORDER BY total_spend_millions DESC nulls last;
```
