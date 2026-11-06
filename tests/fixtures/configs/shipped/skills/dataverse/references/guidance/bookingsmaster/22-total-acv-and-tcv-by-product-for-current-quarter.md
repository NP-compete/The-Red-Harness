<!-- bookingsmaster · from 05-validated-query-templates-1.md -->
### Query 2: Total ACV+ and TCV by Product for Current Quarter

**Business Question**: "What is the total ACV+ by product for current quarter?"

```sql
-- ============================================================================
-- TOTAL ACV+ AND TCV BY PRODUCT - CURRENT QUARTER
-- ============================================================================
-- Purpose: Analyze bookings by product offering group for current quarter
-- Business Rules:
--   - Reports both TCV and ACV+ (most common metrics)
--   - Null product_split_offering_group indicates Discover stage
--   - Exclude zero ACV+ to focus on active products
-- ============================================================================

SELECT
    product_split_offering_group,
    SUM(tcv_amount_usd_cy_pr) as total_tcv_amount_usd,
    SUM(ACV_PLUS_AMOUNT_USD_CY_PR) AS total_acv_plus_usd
FROM
    BOOKINGSMASTER_DB.MARTS.pipeline_transactions_acv
WHERE
    bookings_flag = 'Y'                                    -- Golden filter
    AND trx_crm_forecast_category <> 'Omitted'             -- Exclude omitted
    AND acv_plus_amount_usd_cy_pr <> 0                     -- Exclude zero values
    AND ACV_PLUS_AMOUNT_USD_CY_PR IS NOT NULL              -- Valid values only
    AND TRX_DATE_FISCAL_YEAR_QUARTER = TO_CHAR(CURRENT_DATE, 'YYYY') || '-Q' || TO_CHAR(CEIL(EXTRACT(MONTH FROM CURRENT_DATE) / 3))
GROUP BY
    1
ORDER BY
    product_split_offering_group DESC;

-- IMPORTANT: Null product_split_offering_group can signify the Opportunity is in
-- Discover stage where the sales rep did not start working on the Opportunity to
-- create a quote with products or even have the primary product of interest added.
-- These are valid bookings - the rep needs to pick it up and add products.
-- 📎 AGENT NOTE: Include the [ACV & ARR Calculation Guidance](https://docs.google.com/presentation/d/1gKQ1oJD3wsqmWG7eVBEcg2uJTqrsg9uJhrQ_oeq6Spw/edit#slide=id.g3278c2005cd_8_3536) link in your response.
```

---
