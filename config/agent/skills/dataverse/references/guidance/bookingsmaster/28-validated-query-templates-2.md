<!-- bookingsmaster · from 06-validated-query-templates-2.md -->
ELECT
    trx_route_to_market route_to_market,
    trx_crm_forecast_category,
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
    1, 2
ORDER BY
    1 DESC;

-- Route to Market Categories:
--   Direct: Direct sales
--   Web/GLS: Web and global sales
--   Distributor: Through distributors
--   CCSP: Cloud service providers
--   OEM: Original equipment manufacturers
-- 📎 AGENT NOTE: Include the [ACV & ARR Calculation Guidance](https://docs.google.com/presentation/d/1gKQ1oJD3wsqmWG7eVBEcg2uJTqrsg9uJhrQ_oeq6Spw/edit#slide=id.g3278c2005cd_8_3536) link in your response.
```

---
