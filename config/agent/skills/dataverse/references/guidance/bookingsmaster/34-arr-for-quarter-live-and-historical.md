<!-- bookingsmaster · from 06-validated-query-templates-2.md -->
### Query 12: ARR for Quarter (Live and Historical)

**Business Question**: "What is the total ARR for Q1?" (defaults to current year), "Q1 2025 ARR", or "ARR for Sales Group X for [quarter]"

Use **PIPELINE** for current/future quarter (live). Use **EOQ** for historical quarters; EOQ uses `ACCOUNT_SALES_GROUP_NAME` / `ACCOUNT_GLOBAL_SALES_GROUP_NAME` (not `SALES_GROUP_NAME`). Default to current year when not specified.

```sql
-- ============================================================================
-- LIVE: Current/future quarter (PIPELINE_TRANSACTIONS_ARR)
-- ============================================================================
-- Total ARR for current quarter (add AND SALES_GROUP_NAME = 'X' for one sales group)
SELECT
    revenue_recognition_date_fiscal_year_quarter,
    SUM(trx_projected_arr_amount_usd_cy_pr) AS total_arr_usd
FROM BOOKINGSMASTER_DB.MARTS.pipeline_transactions_arr
WHERE revenue_recognition_date_fiscal_year_quarter = TO_CHAR(CURRENT_DATE, 'YYYY') || '-Q' || TO_CHAR(CEIL(DATE_PART(MONTH, CURRENT_DATE) / 3))
  AND bookings_flag = 'Y'
  AND trx_closed_booking_flag = 'Y'
  AND trx_origin_system <> 'CRM Order'
  AND trx_projected_arr_amount_usd_cy_pr <> 0
  -- AND SALES_GROUP_NAME = 'PORSCHE INFORMATIK'   -- optional: limit to one sales group
GROUP BY revenue_recognition_date_fiscal_year_quarter;

-- ============================================================================
-- HISTORICAL: Completed quarter (EOQ_TRANSACTION_ARR_SNAPSHOT)
-- ============================================================================
-- Total ARR for a past quarter (add AND ACCOUNT_SALES_GROUP_NAME = 'X' for one sales group)
SELECT
    revenue_recognition_date_fiscal_year_quarter,
    SUM(trx_projected_arr_amount_usd_cy_pr) AS total_arr_usd
FROM BOOKINGSMASTER_DB.MARTS.eoq_transaction_arr_snapshot
WHERE revenue_recognition_date_fiscal_year_quarter = '2025-Q1'   -- explicit quarter
  AND bookings_flag = 'Y'
  AND trx_closed_booking_flag = 'Y'
  AND trx_origin_system <> 'CRM Order'
  AND trx_projected_arr_amount_usd_cy_pr <> 0
  -- AND ACCOUNT_SALES_GROUP_NAME = 'PORSCHE INFORMATIK'   -- optional: use ACCOUNT_* for EOQ
GROUP BY revenue_recognition_date_fiscal_year_quarter;
-- Benchmark: Q1 2025 total ARR ≈ $6.26B
-- 📎 AGENT NOTE: Include the [ACV & ARR Calculation Guidance](https://docs.google.com/presentation/d/1gKQ1oJD3wsqmWG7eVBEcg2uJTqrsg9uJhrQ_oeq6Spw/edit#slide=id.g3278c2005cd_8_3536) link in your response.
```

### Query 12a: Annual
