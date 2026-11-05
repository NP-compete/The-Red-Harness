<!-- bookingsmaster · from 05-validated-query-templates-1.md -->
### Query 3: Total ACV for Specific Quarter (User Asks for "ACV")

**Business Question**: "What is the ACV for Q4 2025?" or "Show me Q3 ACV"

```sql
-- ============================================================================
-- TOTAL ACV FOR SPECIFIC QUARTER - ALWAYS REPORT BOTH ACV AND ACV+
-- ============================================================================
-- Purpose: When user asks for "ACV", report ACV+ and TCV
-- Business Rules:
--   - User says "ACV" but means "ACV+" (includes consumption)
--   - Report ACV+ and TCV, do NOT include acv_amount_usd_cy_pr
--   - Default to current year if year not specified
-- ============================================================================

-- Example 1: User says "Q4 2025 ACV" (year specified)
SELECT
    TRX_DATE_FISCAL_YEAR_QUARTER,
    SUM(acv_plus_amount_usd_cy_pr) as total_acv_plus_usd,
    SUM(tcv_amount_usd_cy_pr) as total_tcv_usd
FROM BOOKINGSMASTER_DB.MARTS.EOQ_TRANSACTION_ACV_SNAPSHOT
WHERE TRX_DATE_FISCAL_YEAR_QUARTER = '2025-Q4'  -- User specified 2025
    AND BOOKINGS_FLAG = 'Y'
    AND trx_crm_forecast_category <> 'Omitted'
GROUP BY TRX_DATE_FISCAL_YEAR_QUARTER;

-- Example 2: User says "Q3 ACV" (no year - default to current year)
SELECT
    TRX_DATE_FISCAL_YEAR_QUARTER,
    SUM(acv_plus_amount_usd_cy_pr) as total_acv_plus_usd,
    SUM(tcv_amount_usd_cy_pr) as total_tcv_usd
FROM BOOKINGSMASTER_DB.MARTS.pipeline_transactions_acv
WHERE TRX_DATE_FISCAL_YEAR_QUARTER = TO_CHAR(CURRENT_DATE, 'YYYY') || '-Q3'  -- Current year Q3
    AND bookings_flag = 'Y'
    AND trx_crm_forecast_category <> 'Omitted'
    AND acv_plus_amount_usd_cy_pr <> 0
GROUP BY TRX_DATE_FISCAL_YEAR_QUARTER;

-- CRITICAL NOTES:
-- 1. When user asks for "ACV", they mean "ACV+" — use acv_plus_amount_usd_cy_pr
-- 2. Do NOT include acv_amount_usd_cy_pr alongside acv_plus_amount_usd_cy_pr
-- 3. Default to current year when year not specified in user query
-- 📎 AGENT NOTE: Include the [ACV & ARR Calculation Guidance](https://docs.google.com/presentation/d/1gKQ1oJD3wsqmWG7eVBEcg2uJTqrsg9uJhrQ_oeq6Spw/edit#slide=id.g3278c2005cd_8_3536) link in your response.
```

---
