<!-- bookingsmaster · from 05-validated-query-templates-1.md -->
### Query 4: ACV and ACV+ Performance by Geography and Territory (Historical)

**Business Question**: "How did our ACV and ACV+ performance vary by geographic region and territory in 2025 Q1?"

```sql
-- ============================================================================
-- ACV AND ACV+ PERFORMANCE BY GEOGRAPHY - HISTORICAL QUARTER
-- ============================================================================
-- Purpose: Analyze closed bookings performance by geography for completed quarter
-- Table: Use EOQ_TRANSACTION_ACV_SNAPSHOT for historical analysis
-- ============================================================================

SELECT
    TRX_SPLIT_GEO AS geographic_region,
    TRX_SPLIT_TERRITORY_NAME AS territory,
    SUM(ACV_PLUS_AMOUNT_USD_CY_PR) AS total_acv_plus,
    SUM(TCV_AMOUNT_USD_CY_PR) AS total_tcv
FROM
    BOOKINGSMASTER_DB.MARTS.EOQ_TRANSACTION_ACV_SNAPSHOT    -- Historical snapshot table
WHERE
    TRX_DATE_FISCAL_YEAR_QUARTER = '2025-Q1'                -- Specific quarter
    AND BOOKINGS_FLAG = 'Y'                                  -- Golden filter
GROUP BY
    TRX_SPLIT_GEO,
    TRX_SPLIT_TERRITORY_NAME
ORDER BY
    TRX_SPLIT_GEO,
    TRX_SPLIT_TERRITORY_NAME;

-- Note: For historical analysis, ALWAYS use eoq_transaction_acv_snapshot
-- Note: Geography hierarchy: GEO → REGION → SUBREGION → TERRITORY
-- 📎 AGENT NOTE: Include the [ACV & ARR Calculation Guidance](https://docs.google.com/presentation/d/1gKQ1oJD3wsqmWG7eVBEcg2uJTqrsg9uJhrQ_oeq6Spw/edit#slide=id.g3278c2005cd_8_3536) link in your response.
```

---
