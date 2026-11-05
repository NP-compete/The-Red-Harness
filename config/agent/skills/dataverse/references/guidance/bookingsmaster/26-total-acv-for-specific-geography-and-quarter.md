<!-- bookingsmaster · from 05-validated-query-templates-1.md -->
### Query 5: Total ACV for Specific Geography and Quarter

**Business Question**: "What is the total ACV amount for EMEA in Q2 of 2024?"

```sql
-- ============================================================================
-- TOTAL ACV FOR SPECIFIC GEOGRAPHY - HISTORICAL QUARTER
-- ============================================================================
-- Purpose: Calculate total ACV for a specific geography and quarter
-- Business Rules:
--   - bookings_flag handles IBM Internal exclusion
-- ============================================================================

SELECT
    SUM(ACV_PLUS_AMOUNT_USD_CY_PR) AS total_acv_plus,
    SUM(TCV_AMOUNT_USD_CY_PR) AS total_tcv
FROM
    BOOKINGSMASTER_DB.MARTS.EOQ_TRANSACTION_ACV_SNAPSHOT
WHERE
    TRX_DATE_FISCAL_YEAR_QUARTER = '2024-Q2'
    AND TRX_SPLIT_GEO = 'EMEA_EMEA'
    AND BOOKINGS_FLAG = 'Y'

-- Geography Codes:
--   APAC_APAC, EMEA_EMEA, NA_COMM, NAPS, LATAM, TELCO_TELCO, ALLIANCES_ALLIANCES
-- 📎 AGENT NOTE: Include the [ACV & ARR Calculation Guidance](https://docs.google.com/presentation/d/1gKQ1oJD3wsqmWG7eVBEcg2uJTqrsg9uJhrQ_oeq6Spw/edit#slide=id.g3278c2005cd_8_3536) link in your response.
```

---
