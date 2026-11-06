<!-- bookingsmaster · from 10-common-mistakes-to-avoid.md -->
### 10. ❌ Using Wrong Column Names Between ARR Tables

**Wrong** (using pipeline column names in EOQ table):
```sql
-- Historical ARR for Sales Group - WRONG
SELECT account_sales_group_name
FROM BOOKINGSMASTER_DB.MARTS.eoq_transaction_arr_snapshot
WHERE sales_group_name = 'PORSCHE INFORMATIK';  -- Column doesn't exist in EOQ!
```

**Right**:
```sql
-- Use correct column names for each table
SELECT ACCOUNT_SALES_GROUP_NAME,
       SUM(trx_projected_arr_amount_usd_cy_pr) AS total_arr_usd
FROM BOOKINGSMASTER_DB.MARTS.eoq_transaction_arr_snapshot
WHERE ACCOUNT_SALES_GROUP_NAME = 'PORSCHE INFORMATIK'  -- Correct for EOQ table
  AND revenue_recognition_date_fiscal_year_quarter = '2025-Q1'
  AND bookings_flag = 'Y'
  AND trx_closed_booking_flag = 'Y'
  AND trx_origin_system <> 'CRM Order'
  AND trx_projected_arr_amount_usd_cy_pr <> 0
GROUP BY ACCOUNT_SALES_GROUP_NAME;
```

**Rule**: PIPELINE_TRANSACTIONS_ARR uses `SALES_GROUP_NAME` / `GLOBAL_SALES_GROUP_NAME`. EOQ_TRANSACTION_ARR_SNAPSHOT uses `ACCOUNT_SALES_GROUP_NAME` / `ACCOUNT_GLOBAL_SALES_GROUP_NAME`. Using the wrong pair causes compilation errors or inflated totals.

---

### 11. ❌ Restricting to a Single Quarter When User Asked for Full Year (CY/FY/Year)

```sql
-- ❌ WRONG: "CY25 ACV+" filtered to one quarter
WHERE TRX_DATE_FISCAL_YEAR_QUARTER = '2025-Q1'

-- ✅ RIGHT: CY25/FY25/2025 = full year — use TRX_DATE_FISCAL_YEAR_NUMBER
WHERE TRX_DATE_FISCAL_YEAR_NUMBER = 2025
```

---
