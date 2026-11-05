<!-- expensemaster · from 11-it-forecast-future-spend-apptio-tables-2.md -->
uestion**: What would be the effect of terminating PO 1010106429 immediately?

**Methodology:**

1. **Actual Cost**: From contract start to current month - 1 (from `ITPF_FORECAST_DAILY_CURRENT`)
2. **Future Cost**: From current month to contract end (from `ITPF_CONTRACT_FORECAST_W_DELEGATION`)
3. **Money Saved**: The future cost represents savings from termination

```sql
WITH contract AS (
  SELECT DISTINCT PO_NUMBER, VENDOR, DESCRIPTION, CONTRACT_TYPE,
    TO_DATE(START_DATE) as START_DT, TO_DATE(END_DATE) as END_DT
  FROM EXPENSEMASTER_DB.RHAI_MARTS.ITPF_CONTRACT_FORECAST_W_DELEGATION
  WHERE PO_NUMBER = '1010106429'
),
actuals AS (
  SELECT PO_NUMBER, period_date, PERIOD_AMOUNT
  FROM EXPENSEMASTER_DB.RHAI_MARTS.ITPF_FORECAST_DAILY_CURRENT
  WHERE PO_NUMBER = '1010106429'
    AND PERIOD_AMOUNT > 0
    AND forecast_entry_month = (SELECT MAX(forecast_entry_month) FROM EXPENSEMASTER_DB.RHAI_MARTS.ITPF_FORECAST_DAILY_CURRENT)
    AND period_date < DATE_TRUNC('month', CURRENT_DATE())
),
forecasts AS (
  SELECT PO_NUMBER, period_date, PERIOD_AMOUNT
  FROM EXPENSEMASTER_DB.RHAI_MARTS.ITPF_CONTRACT_FORECAST_W_DELEGATION
  WHERE PO_NUMBER = '1010106429'
    AND PERIOD_AMOUNT > 0
    AND period_date >= DATE_TRUNC('month', CURRENT_DATE())
),
summary AS (
  SELECT
    SUM(a.PERIOD_AMOUNT) as SPENT,
    SUM(f.PERIOD_AMOUNT) as SAVE
  FROM (SELECT SUM(PERIOD_AMOUNT) as PERIOD_AMOUNT FROM actuals) a,
       (SELECT SUM(PERIOD_AMOUNT) as PERIOD_AMOUNT FROM forecasts) f
)
SELECT
  'Using Apptio data, which includes spend that resides in IT cost centers.' AS _filter_note,
  ct.VENDOR,
  TO_VARCHAR(ct.START_DT,'YYYY-MM-DD') || ' to ' || TO_VARCHAR(ct.END_DT,'YYYY-MM-DD') as CONTRACT_PERIOD,
  s.SPENT as ACTUAL_COST,
  s.SAVE as AVOIDABLE_COST,
  ROUND(s.SAVE/(s.SPENT + s.SAVE)*100,1) as PCT_SAVINGS
FROM contract ct
CROSS JOIN summary s;
```
