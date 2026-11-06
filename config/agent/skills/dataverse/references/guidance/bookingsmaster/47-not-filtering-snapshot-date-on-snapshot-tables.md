<!-- bookingsmaster · from 10-common-mistakes-to-avoid.md -->
### 5. ❌ Not Filtering snapshot_date on Snapshot Tables

**Wrong** (will timeout - 695M+ records!):
```sql
SELECT *
FROM pipeline_transactions_acv_snapshot
WHERE bookings_flag = 'Y'
-- Missing snapshot_date filter!
```

**Right**:
```sql
SELECT *
FROM pipeline_transactions_acv_snapshot
WHERE bookings_flag = 'Y'
  AND snapshot_date = (SELECT MAX(snapshot_date) FROM pipeline_transactions_acv_snapshot)
```

---

### 6. ❌ Using Raw Amount Fields Instead of USD Converted

**Wrong**:
```sql
SELECT SUM(acv_amount)  -- NO! Currency mix issues
```

**Right**:
```sql
SELECT SUM(acv_plus_amount_usd_cy_pr)  -- YES! Pre-converted to USD
```

---
