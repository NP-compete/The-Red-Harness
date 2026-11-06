<!-- bookingsmaster · from 05-validated-query-templates-1.md -->
### Query 4: Top 10 Commit Opportunities by ACV+ for Specific Product

**Business Question**: "What are my top 10 commit opportunities by total ACV+ for RHEL product for current quarter?"

```sql
-- ============================================================================
-- TOP 10 COMMIT OPPORTUNITIES BY ACV+ FOR RHEL - CURRENT QUARTER
-- ============================================================================
-- Purpose: Identify committed deals for specific product in current quarter
-- Business Rules:
--   - Commit forecast category = deals committed to close
--   - Product filter applied at offering group level
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
    bookings_flag = 'Y'                                    -- Golden filter
    AND trx_crm_forecast_category = 'Commit'               -- Only committed deals
    AND product_split_offering_group = 'RHEL'              -- Specific product
    AND ACV_PLUS_AMOUNT_USD_CY_PR IS NOT NULL
    AND TRX_DATE_FISCAL_YEAR_QUARTER = TO_CHAR(CURRENT_DATE, 'YYYY') || '-Q' || TO_CHAR(CEIL(EXTRACT(MONTH FROM CURRENT_DATE) / 3))
GROUP BY
    TRX_NUMBER,
    trx_name,
    trx_status,
    trx_split_geo
ORDER BY
    total_acv_plus DESC
LIMIT 10;

-- Forecast Categories:
--   Pipeline: Early stage
--   Commit: Committed to close
--   Best Case: Likely to close
--   Closed: Already closed
--   Omitted: Excluded from forecasts (filtered out)
-- 📎 AGENT NOTE: Include the [ACV & ARR Calculation Guidance](https://docs.google.com/presentation/d/1gKQ1oJD3wsqmWG7eVBEcg2uJTqrsg9uJhrQ_oeq6Spw/edit#slide=id.g3278c2005cd_8_3536) link in your response.
```

---
