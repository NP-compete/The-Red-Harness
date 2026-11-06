<!-- bookingsmaster · from 07-validated-query-templates-3.md -->
### Query 13: ARR for Specific Company

**Business Question**: "What is the ARR for Walmart?" or "Show me Walmart's ARR for Q3"

```sql
-- ============================================================================
-- ARR FOR SPECIFIC COMPANY
-- ============================================================================
-- Purpose: Calculate ARR for a specific company
-- Business Rules:
--   - Use global_sales_group_name (preferred) or sales_group_name
--   - NEVER use mdm_party_name for aggregation
--   - Present options if company name is ambiguous
--   - Default to current year if not specified
-- ============================================================================

-- Step 1: If company name is ambiguous, show options to user
SELECT DISTINCT
    global_sales_group_name,
    sales_group_name,
    SUM(trx_projected_arr_amount_usd_cy_pr) as arr_amount
FROM bookingsmaster_db.marts.pipeline_transactions_arr
WHERE (global_sales_group_name ILIKE '%Walmart%'
    OR sales_group_name ILIKE '%Walmart%')
    AND revenue_recognition_date_fiscal_year_quarter = TO_CHAR(CURRENT_DATE, 'YYYY') || '-Q3'  -- Current year Q3
    AND bookings_flag = 'Y'
    AND trx_closed_booking_flag = 'Y'
    AND trx_origin_system <> 'CRM Order'
    AND trx_projected_arr_amount_usd_cy_pr <> 0
GROUP BY global_sales_group_name, sales_group_name
ORDER BY arr_amount DESC
LIMIT 10;

-- Step 2: After user confirms, use exact global_sales_group_name
SELECT
    global_sales_group_name,
    revenue_recognition_date_fiscal_year_quarter,
    SUM(trx_projected_arr_amount_usd_cy_pr) as total_arr
FROM bookingsmaster_db.marts.pipeline_transactions_arr
WHERE global_sales_group_name = 'Walmart Inc'  -- Exact match after user confirmation
    AND revenue_recognition_date_fiscal_year_quarter = TO_CHAR(CURRENT_DATE, 'YYYY') || '-Q3'
    AND bookings_flag = 'Y'
    AND trx_closed_booking_flag = 'Y'
    AND trx_origin_system <> 'CRM Order'
    AND trx_projected_arr_amount_usd_cy_pr <> 0
GROUP BY global_sales_group_name, revenue_recognition_date_fiscal_year_quarter;

-- KEY NOTES:
-- - Use global_sales_group_name for company-level aggregation
-- - Use sales_group_name for sales group analysis
-- - NEVER use mdm_party_name for ARR aggregation
-- - Always default to current year when not specified
-- - For historical quarters use eoq_transaction_arr_snapshot and ACCOUNT_GLOBAL_SALES_GROUP_NAME / ACCOUNT_SALES_GROUP_NAME
-- 📎 AGENT NOTE: Include the [ACV & ARR Calculation Guidance](https://docs.google.com/presentation/d/1gKQ1oJD3wsqmWG7eVBEcg2uJTqrsg9uJhrQ_oeq6Spw/edit#slide=id.g3278c2005cd_8_3536) link in your response.
```
