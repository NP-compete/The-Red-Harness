<!-- bookingsmaster · from 08-validated-query-templates-4.md -->
uding product code MCT0001
SELECT
    COUNT(DISTINCT TRX_NUMBER) AS total_hcs_commitments,
    SUM(ACV_PLUS_AMOUNT_USD_CY_PR) AS total_acv_plus_usd,
    SUM(TCV_AMOUNT_USD_CY_PR) AS total_tcv_usd
FROM
    BOOKINGSMASTER_DB.MARTS.PIPELINE_TRANSACTIONS_ACV
WHERE
    bookings_flag = 'Y'
    AND trx_crm_forecast_category <> 'Omitted'
    AND TRX_HYBRID_COMMITTED_SPEND_EVENT_TYPE = 'HCS Commitment'
    AND PRODUCT_CODE <> 'MCT0001'
    AND TRX_DATE_FISCAL_YEAR_NUMBER = 2026
    AND trx_closed_booking_flag = 'Y';

-- Variant: ECS Commitments (change event type)
-- AND TRX_HYBRID_COMMITTED_SPEND_EVENT_TYPE = 'ECS Commitment'

-- Variant: With opportunity-level detail
SELECT
    TRX_NUMBER AS opportunity_number,
    trx_name AS opportunity_name,
    trx_split_geo AS geo,
    PRODUCT_CODE,
    SUM(ACV_PLUS_AMOUNT_USD_CY_PR) AS total_acv_plus_usd,
    SUM(TCV_AMOUNT_USD_CY_PR) AS total_tcv_usd
FROM
    BOOKINGSMASTER_DB.MARTS.PIPELINE_TRANSACTIONS_ACV
WHERE
    bookings_flag = 'Y'
    AND trx_crm_forecast_category <> 'Omitted'
    AND TRX_HYBRID_COMMITTED_SPEND_EVENT_TYPE = 'HCS Commitment'
    AND PRODUCT_CODE <> 'MCT0001'
    AND TRX_DATE_FISCAL_YEAR_NUMBER = 2026
    AND trx_closed_booking_flag = 'Y'
GROUP BY
    TRX_NUMBER, trx_name, trx_split_geo, PRODUCT_CODE
ORDER BY
    total_acv_plus_usd DESC;

-- For historical years, use eoq_transaction_acv_snapshot:
-- FROM BOOKINGSMASTER_DB.MARTS.EOQ_TRANSACTION_ACV_SNAPSHOT

-- HCS/ECS KEY COLUMNS:
--   TRX_HYBRID_COMMITTED_SPEND_EVENT_TYPE: 'HCS Commitment', 'ECS Commitment'
--   PRODUCT_CODE: Product code for line-level filtering (e.g., MCT0001)
--   HCS_COMMITMENT_CONTRACT_ID: HCS contract identifier
--   HCS_COMMITMENT_OPPORTUNITY_ID: HCS opportunity identifier
--   HCS_COMMITMENT_FISCAL_YEAR: Fiscal year of the HCS commitment
--   HCS_DRAWDOWN_FLAG: Indicates if transaction is an HCS drawdown
--   TRX_COMMIT_FLAG: General commitment flag
--   ACV_PLUS_AMOUNT_DRAWDOWN_USD_CY_PR: Drawdown-specific ACV+ metric
-- 📎 AGENT NOTE: Include the [ACV & ARR Calculation Guidance](https://docs.google.com/presentation/d/1gKQ1oJD3wsqmWG7eVBEcg2uJTqrsg9uJhrQ_oeq6Spw/edit#slide=id.g3278c2005cd_8_3536) link in your response.
```

---
