<!-- bookingsmaster · from 10-common-mistakes-to-avoid.md -->
### 3. ❌ Using Wrong Table for Time Period

**Wrong** (using live table for historical):
```sql
-- Querying Q1 2024 (completed quarter) from live table
SELECT *
FROM pipeline_transactions_acv
WHERE TRX_DATE_FISCAL_YEAR_QUARTER = '2024-Q1'
```

**Right**:
```sql
-- Use snapshot table for historical/completed quarters
SELECT *
FROM eoq_transaction_acv_snapshot
WHERE TRX_DATE_FISCAL_YEAR_QUARTER = '2024-Q1'
```

---
