<!-- bookingsmaster · from 06-validated-query-templates-2.md -->
### Query 8: Current Quarter Closed vs Open Bookings

**Business Question**: "How much we have booked for current quarter and how much is open?"

```sql
-- ============================================================================
-- CLOSED VS OPEN BOOKINGS - CURRENT QUARTER
-- ============================================================================
-- Purpose: Show split between closed deals and open pipeline
-- Business Rules:
--   - trx_closed_booking_flag determines if deal is closed
--   - This is different from bookings_flag (which determines if it counts as booking)
-- ============================================================================

SELECT
    CASE
        WHEN trx_closed_booking_flag = 'Y' THEN 'Closed Booked'
        ELSE 'Open'
    END closed_booked_flag,
    SUM(tcv_amount_usd_cy_pr) as total_tcv_amount_usd,
    SUM(ACV_PLUS_AMOUNT_USD_CY_PR) AS total_acv_plus_usd
FROM
    BOOKINGSMASTER_DB.MARTS.pipeline_transactions_acv
WHERE
    bookings_flag = 'Y'
    AND trx_crm_forecast_category <> 'Omitted'
    AND acv_plus_amount_usd_cy_pr <> 0
    AND ACV_PLUS_AMOUNT_USD_CY_PR IS NOT NULL
    AND TRX_DATE_FISCAL_YEAR_QUARTER = TO_CHAR(CURRENT_DATE, 'YYYY') || '-Q' || TO_CHAR(CEIL(EXTRACT(MONTH FROM CURRENT_DATE) / 3))
GROUP BY
    1;

-- Key Distinction:
--   bookings_flag = 'Y': Determines if transaction counts as a booking (product rules, exclusions)
--   trx_closed_booking_flag = 'Y': Determines if the deal is closed vs open
-- 📎 AGENT NOTE: Include the [ACV & ARR Calculation Guidance](https://docs.google.com/presentation/d/1gKQ1oJD3wsqmWG7eVBEcg2uJTqrsg9uJhrQ_oeq6Spw/edit#slide=id.g3278c2005cd_8_3536) link in your response.
```

---
