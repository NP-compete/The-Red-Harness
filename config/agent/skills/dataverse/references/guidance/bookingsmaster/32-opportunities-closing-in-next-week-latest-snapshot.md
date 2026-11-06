<!-- bookingsmaster · from 06-validated-query-templates-2.md -->
### Query 10: Opportunities Closing in Next Week (Latest Snapshot)

**Business Question**: "What are the top 20 opportunities that supposed to be closed in the next week?"

```sql
-- ============================================================================
-- OPPORTUNITIES CLOSING NEXT WEEK - LATEST SNAPSHOT
-- ============================================================================
-- Purpose: Identify near-term pipeline conversion opportunities
-- Table: pipeline_transactions_acv_snapshot for latest point-in-time view
-- Business Rules:
--   - MUST use latest snapshot_date for accurate pipeline view
--   - Only open opportunities (trx_closed_booking_flag = 'N')
-- ============================================================================

SELECT
    TRX_NUMBER AS opportunity_number,
    SUM(ACV_PLUS_AMOUNT_USD_CY_PR) AS acv_plus_usd
FROM
    BOOKINGSMASTER_DB.MARTS.PIPELINE_TRANSACTIONS_ACV_SNAPSHOT
WHERE
    TRX_CLOSED_BOOKING_FLAG = 'N'                           -- Open opportunities only
    AND bookings_flag = 'Y'
    AND snapshot_date = (
        SELECT MAX(snapshot_date)
        FROM BOOKINGSMASTER_DB.MARTS.pipeline_transactions_acv_snapshot
    )                                                        -- Latest snapshot only
    AND TRX_DATE >= CURRENT_DATE()                           -- Close date is future
    AND TRX_DATE <= DATEADD(day, 7, CURRENT_DATE())        -- Within next 7 days
    AND ACV_PLUS_AMOUNT_USD_CY_PR <> 0
GROUP BY
    TRX_NUMBER
ORDER BY
    acv_plus_usd DESC
LIMIT 20;

-- CRITICAL: pipeline_transactions_acv_snapshot has 695M+ records
-- ALWAYS filter by snapshot_date to avoid timeouts
-- 📎 AGENT NOTE: Include the [ACV & ARR Calculation Guidance](https://docs.google.com/presentation/d/1gKQ1oJD3wsqmWG7eVBEcg2uJTqrsg9uJhrQ_oeq6Spw/edit#slide=id.g3278c2005cd_8_3536) link in your response.
```

---
