<!-- expensemaster · from 09-golden-query-templates-gl-onestream-2.md -->
### 7.8 What is the total spend for a specific quarter?

**Time Period Conversion**:
- **Q1**: `MONTH(period_date) IN (1, 2, 3)`
- **Q2**: `MONTH(period_date) IN (4, 5, 6)`
- **Q3**: `MONTH(period_date) IN (7, 8, 9)`
- **Q4**: `MONTH(period_date) IN (10, 11, 12)`

```sql
-- Example: Q1 of current year (default when no year specified)
SELECT
    SUM(amount_usd) as total_spend
FROM EXPENSEMASTER_DB.RHAI_MARTS.GL_SUB_LEDGER_AGGREGATE
WHERE YEAR(period_date) = YEAR(CURRENT_DATE())
  AND MONTH(period_date) IN (1, 2, 3);
```

---
