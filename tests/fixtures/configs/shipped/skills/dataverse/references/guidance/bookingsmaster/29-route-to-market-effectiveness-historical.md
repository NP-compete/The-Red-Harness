<!-- bookingsmaster · from 06-validated-query-templates-2.md -->
### Query 7: Route to Market Effectiveness (Historical)

**Business Question**: "How effective were our different routes to market in Q1'25?"

```sql
-- ============================================================================
-- ROUTE TO MARKET EFFECTIVENESS - HISTORICAL QUARTER
-- ============================================================================
-- Purpose: Evaluate which sales channels were most effective
-- ============================================================================

SELECT
    TRX_ROUTE_TO_MARKET,
    SUM(ACV_PLUS_AMOUNT_USD_CY_PR) AS Total_ACV_Plus,
    SUM(TCV_AMOUNT_USD_CY_PR) AS Total_TCV
FROM
    BOOKINGSMASTER_DB.MARTS.EOQ_TRANSACTION_ACV_SNAPSHOT
WHERE
    TRX_DATE_FISCAL_YEAR_QUARTER = '2025-Q1'
    AND BOOKINGS_FLAG = 'Y'
GROUP BY
    TRX_ROUTE_TO_MARKET
ORDER BY
    Total_ACV DESC;
-- 📎 AGENT NOTE: Include the [ACV & ARR Calculation Guidance](https://docs.google.com/presentation/d/1gKQ1oJD3wsqmWG7eVBEcg2uJTqrsg9uJhrQ_oeq6Spw/edit#slide=id.g3278c2005cd_8_3536) link in your response.
```

---
