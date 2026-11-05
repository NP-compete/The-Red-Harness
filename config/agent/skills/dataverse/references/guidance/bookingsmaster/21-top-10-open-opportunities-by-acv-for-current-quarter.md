<!-- bookingsmaster · from 05-validated-query-templates-1.md -->
### Query 1: Top 10 Open Opportunities by ACV+ for Current Quarter

**Business Question**: "Get me the top 10 open opportunities by total ACV+ by geo for the current quarter"

```sql
-- ============================================================================
-- TOP 10 OPEN OPPORTUNITIES BY TOTAL ACV+ BY GEO - CURRENT QUARTER
-- ============================================================================
-- Purpose: Identify largest open opportunities for current quarter pipeline
-- Business Rules:
--   - bookings_flag = 'Y': Applies all product inclusion/exclusion rules
--   - Exclude Omitted: Only count opportunities in active forecast categories
--   - Open opportunities: Determined by forecast category, not closed flag
-- ============================================================================

SELECT
    TRX_NUMBER AS opportunity_number,
    trx_name as opportunity_name,
    trx_status as opportunity_stage,
    trx_split_geo as geo,
    SUM(ACV_PLUS_AMOUNT_USD_CY_PR) AS total_acv_plus
FROM
    BOOKINGSMASTER_DB.MARTS.pipeline_transactions_acv
WHERE
    bookings_flag = 'Y'                                    -- Golden filter: includes all booking rules
    AND trx_crm_forecast_category <> 'Omitted'             -- Exclude omitted opportunities
    AND ACV_PLUS_AMOUNT_USD_CY_PR IS NOT NULL              -- Valid ACV+ values only
    AND TRX_DATE_FISCAL_YEAR_QUARTER = TO_CHAR(CURRENT_DATE, 'YYYY') || '-Q' || TO_CHAR(CEIL(EXTRACT(MONTH FROM CURRENT_DATE) / 3))  -- Dynamic current quarter
GROUP BY
    TRX_NUMBER,
    trx_name,
    trx_status,
    trx_split_geo
ORDER BY
    total_acv_plus DESC
LIMIT 10;

-- Note: trx_status shows opportunity stage (Discover, Engage, Validate, Propose, Negotiate)
-- Note: For closed opportunities, add filter: trx_closed_booking_flag = 'Y'
-- 📎 AGENT NOTE: Include the [ACV & ARR Calculation Guidance](https://docs.google.com/presentation/d/1gKQ1oJD3wsqmWG7eVBEcg2uJTqrsg9uJhrQ_oeq6Spw/edit#slide=id.g3278c2005cd_8_3536) link in your response.
```

---
