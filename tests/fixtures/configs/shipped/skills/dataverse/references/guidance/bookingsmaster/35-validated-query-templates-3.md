<!-- bookingsmaster · from 07-validated-query-templates-3.md -->
ARR (Year-End ARR)

**Business Question**: "What is the ARR for 2024?" or "Show me annual ARR for 2024" or "What is 2024 year-end ARR?"

**⚠️ CRITICAL**: Annual ARR = ARR as of end of Q4 (NOT sum of all quarters)

```sql
-- ============================================================================
-- ANNUAL ARR (YEAR-END ARR)
-- ============================================================================
-- Purpose: Calculate annual ARR for a specific year
-- Business Rules:
--   - ARR is a POINT-IN-TIME metric, not a sum
--   - Annual ARR = ARR as of end of Q4 of that year
--   - Do NOT sum Q1 + Q2 + Q3 + Q4 (this is WRONG)
--   - Use eoq_transaction_arr_snapshot for historical years
--   - Use pipeline_transactions_arr for current year (if Q4 is complete)
-- ============================================================================

-- Example 1: Annual ARR for 2024 (historical year) - Use Q4 only
SELECT
    revenue_recognition_date_fiscal_year_quarter,
    SUM(trx_projected_arr_amount_usd_cy_pr) AS annual_arr_2024
FROM bookingsmaster_db.marts.eoq_transaction_arr_snapshot
WHERE revenue_recognition_date_fiscal_year_quarter = '2024-Q4'  -- Q4 only, NOT all quarters!
  AND bookings_flag = 'Y'
  AND trx_closed_booking_flag = 'Y'
  AND trx_origin_system <> 'CRM Order'
  AND trx_projected_arr_amount_usd_cy_pr <> 0
GROUP BY revenue_recognition_date_fiscal_year_quarter;

-- Example 2: Annual ARR for current year (if Q4 is complete)
-- If current date is after Q4 end, use Q4 of current year
SELECT
    revenue_recognition_date_fiscal_year_quarter,
    SUM(trx_projected_arr_amount_usd_cy_pr) AS annual_arr
FROM bookingsmaster_db.marts.eoq_transaction_arr_snapshot
WHERE revenue_recognition_date_fiscal_year_quarter = TO_CHAR(CURRENT_DATE, 'YYYY') || '-Q4'
  AND bookings_flag = 'Y'
  AND trx_closed_booking_flag = 'Y'
  AND trx_origin_system <> 'CRM Order'
  AND trx_projected_arr_amount_usd_cy_pr <> 0
GROUP BY revenue_recognition_date_fiscal_year_quarter;

-- ❌ WRONG: Do NOT sum all quarters for annual ARR
-- WHERE revenue_recognition_date_fiscal_year_quarter IN ('2024-Q1', '2024-Q2', '2024-Q3', '2024-Q4')
-- This would incorrectly sum all quarters, which is NOT how annual ARR works

-- KEY NOTES:
-- - Annual ARR = ARR as of end of Q4 (point-in-time metric)
-- - ARR represents cumulative recurring revenue position at year-end
-- - Do NOT sum quarters - Q4 already contains the cumulative ARR
-- - For current year: Use Q4 if complete, otherwise use latest available quarter
-- 📎 AGENT NOTE: Include the [ACV & ARR Calculation Guidance](https://docs.google.com/presentation/d/1gKQ1oJD3wsqmWG7eVBEcg2uJTqrsg9uJhrQ_oeq6Spw/edit#slide=id.g3278c2005cd_8_3536) link in your response.
```
