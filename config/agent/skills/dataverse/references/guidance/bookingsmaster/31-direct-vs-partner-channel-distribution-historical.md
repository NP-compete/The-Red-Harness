<!-- bookingsmaster · from 06-validated-query-templates-2.md -->
### Query 9: Direct vs Partner Channel Distribution (Historical)

**Business Question**: "How are sales distributed across our direct vs. partner channels in last year?"

```sql
-- ============================================================================
-- DIRECT VS PARTNER CHANNEL DISTRIBUTION - PRIOR YEAR
-- ============================================================================
-- Purpose: Analyze sales channel mix for completed fiscal year
-- Business Rules:
--   - Groups route to market into simplified Direct/Partner categories
-- ============================================================================

SELECT
    TRX_DATE_FISCAL_YEAR_NUMBER AS FISCAL_YEAR,
    CASE
        WHEN TRX_ROUTE_TO_MARKET IN ('Direct', 'Web/GLS') THEN 'Direct'
        WHEN TRX_ROUTE_TO_MARKET IN ('Distributor', 'CCSP', 'OEM') THEN 'Partner'
        ELSE 'Other'
    END AS SALES_CHANNEL,
    SUM(ACV_PLUS_AMOUNT_USD_CY_PR) AS TOTAL_ACV_PLUS,
    SUM(TCV_AMOUNT_USD_CY_PR) AS TOTAL_TCV
FROM
    BOOKINGSMASTER_DB.MARTS.EOQ_TRANSACTION_ACV_SNAPSHOT
WHERE
    TRX_DATE_FISCAL_YEAR_NUMBER = (
        SELECT MAX(TRX_DATE_FISCAL_YEAR_NUMBER)
        FROM BOOKINGSMASTER_DB.MARTS.EOQ_TRANSACTION_ACV_SNAPSHOT
    ) - 1                                                    -- Prior year
    AND BOOKINGS_FLAG = 'Y'
GROUP BY
    TRX_DATE_FISCAL_YEAR_NUMBER,
    SALES_CHANNEL
ORDER BY
    TRX_DATE_FISCAL_YEAR_NUMBER,
    SALES_CHANNEL;
-- 📎 AGENT NOTE: Include the [ACV & ARR Calculation Guidance](https://docs.google.com/presentation/d/1gKQ1oJD3wsqmWG7eVBEcg2uJTqrsg9uJhrQ_oeq6Spw/edit#slide=id.g3278c2005cd_8_3536) link in your response.
```

---
