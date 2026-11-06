<!-- bookingsmaster · from 06-validated-query-templates-2.md -->
### Query 11: ACV+ Pipeline for Specific Segment and Geography

**Business Question**: "What is the total ACV+ pipeline for North America Enterprise segment for the current quarter?"

```sql
-- ============================================================================
-- ACV+ PIPELINE BY SEGMENT AND GEOGRAPHY - CURRENT QUARTER
-- ============================================================================
-- Purpose: Analyze open pipeline for specific segment and region
-- Business Rules:
--   - Uses latest snapshot for most accurate pipeline view
--   - Filters by account segment and geography
--   - Open pipeline only (trx_closed_booking_flag = 'N')
-- ============================================================================

SELECT
    SUM(acv_plus_amount_usd_cy_pr) AS acv_amount
FROM
    BOOKINGSMASTER_DB.MARTS.PIPELINE_TRANSACTIONS_ACV_SNAPSHOT
WHERE
    trx_account_segment = 'Enterprise'                      -- Account segment
    AND TRX_SPLIT_GEO IN ('NA_COMM', 'NAPS')               -- North America regions
    AND SNAPSHOT_DATE = (
        SELECT MAX(snapshot_date)
        FROM BOOKINGSMASTER_DB.MARTS.PIPELINE_TRANSACTIONS_ACV_SNAPSHOT
    )
    AND trx_date_fiscal_year_quarter = TO_CHAR(CURRENT_DATE, 'YYYY') || '-Q' || TO_CHAR(CEIL(EXTRACT(MONTH FROM CURRENT_DATE) / 3))
    AND trx_closed_booking_flag = 'N';                      -- Open pipeline only

-- Account Segments:
--   Enterprise: Large enterprise accounts
--   Commercial: Mid-market accounts
--   Strategic: Strategic/key accounts
-- 📎 AGENT NOTE: Include the [ACV & ARR Calculation Guidance](https://docs.google.com/presentation/d/1gKQ1oJD3wsqmWG7eVBEcg2uJTqrsg9uJhrQ_oeq6Spw/edit#slide=id.g3278c2005cd_8_3536) link in your response.
```
