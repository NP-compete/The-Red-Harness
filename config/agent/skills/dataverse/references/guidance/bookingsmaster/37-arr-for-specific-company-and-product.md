<!-- bookingsmaster · from 07-validated-query-templates-3.md -->
### Query 14: ARR for Specific Company and Product

**Business Question**: "What is Walmart's ARR for RHEL?" or "Show me Google's OpenShift ARR for Q2"

```sql
-- ============================================================================
-- ARR FOR SPECIFIC COMPANY AND PRODUCT
-- ============================================================================
-- Purpose: Calculate ARR for specific company and product
-- Business Rules:
--   - Use product_split_offering_group for product filter
--   - Use global_sales_group_name for company aggregation
--   - NEVER use product_description or opportunity_name with LIKE
--   - Default to current year/quarter when not specified
-- ============================================================================

SELECT
    global_sales_group_name,
    product_split_offering_group,
    revenue_recognition_date_fiscal_year_quarter,
    SUM(trx_projected_arr_amount_usd_cy_pr) as total_arr
FROM bookingsmaster_db.marts.pipeline_transactions_arr
WHERE global_sales_group_name = 'Walmart Inc'  -- Company filter
    AND product_split_offering_group = 'RHEL'  -- ✅ CORRECT: Use offering group
    AND revenue_recognition_date_fiscal_year_quarter = TO_CHAR(CURRENT_DATE, 'YYYY') || '-Q2'  -- Current year Q2
    AND bookings_flag = 'Y'
    AND trx_closed_booking_flag = 'Y'
    AND trx_origin_system <> 'CRM Order'
    AND trx_projected_arr_amount_usd_cy_pr <> 0
GROUP BY global_sales_group_name, product_split_offering_group, revenue_recognition_date_fiscal_year_quarter;

-- ❌ WRONG APPROACHES - DO NOT USE:
-- WHERE product_description ILIKE '%RHEL%'  -- Unreliable!
-- WHERE trx_name ILIKE '%Red Hat Enterprise Linux%'  -- Unreliable!
-- WHERE mdm_party_name = 'Walmart'  -- Wrong aggregation field!

-- KEY NOTES:
-- - Use product_split_offering_group (not product_description)
-- - Use global_sales_group_name (not mdm_party_name)
-- - Default to current year when user doesn't specify
-- - For historical quarters use eoq_transaction_arr_snapshot and ACCOUNT_* columns
-- 📎 AGENT NOTE: Include the [ACV & ARR Calculation Guidance](https://docs.google.com/presentation/d/1gKQ1oJD3wsqmWG7eVBEcg2uJTqrsg9uJhrQ_oeq6Spw/edit#slide=id.g3278c2005cd_8_3536) link in your response.
```

---
