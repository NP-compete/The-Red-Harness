<!-- bookingsmaster · from 07-validated-query-templates-3.md -->
### Query 15: GPS/GLS (Consulting/Training) Bookings by Quarter

**Business Question**: "What were GPS and GLS bookings in 2025?", "Break down Services by Consulting and Training", "What were Consulting and Training ACV+ by quarter?"

**⚠️ CRITICAL**: Use `PRODUCT_OFFERING_CATEGORY LIKE 'CONSULTING%'` / `LIKE 'TRAINING%'` — NOT exact match. Multiple subcategories exist (e.g., `CONSULTING - FIXED PRICE`, `TRAINING - ONLINE LEARNING`).

```sql
-- ============================================================================
-- GPS/GLS (CONSULTING/TRAINING) BOOKINGS BY QUARTER
-- ============================================================================
-- Purpose: Break down Services bookings into GPS (Consulting) and GLS (Training)
-- Business Rules:
--   - GPS = all PRODUCT_OFFERING_CATEGORY starting with 'CONSULTING'
--   - GLS = all PRODUCT_OFFERING_CATEGORY starting with 'TRAINING'
--   - Must use LIKE (not = or IN) because subcategories exist
-- Validated: GPS ≈ $563M, GLS ≈ $122M, Total ≈ $685M for FY2025
-- ============================================================================

SELECT
    CASE
        WHEN PRODUCT_OFFERING_CATEGORY LIKE 'CONSULTING%' THEN 'GPS'
        WHEN PRODUCT_OFFERING_CATEGORY LIKE 'TRAINING%' THEN 'GLS'
    END AS SERVICE_GROUP,
    TRX_DATE_FISCAL_YEAR_QUARTER,
    SUM(ACV_PLUS_AMOUNT_USD_CY_PR) AS TOTAL_ACV_PLUS_USD
FROM BOOKINGSMASTER_DB.MARTS.EOQ_TRANSACTION_ACV_SNAPSHOT
WHERE BOOKINGS_FLAG = 'Y'
    AND (PRODUCT_OFFERING_CATEGORY LIKE 'CONSULTING%' OR PRODUCT_OFFERING_CATEGORY LIKE 'TRAINING%')
    AND TRX_CRM_FORECAST_CATEGORY <> 'Omitted'
    AND TRX_DATE_FISCAL_YEAR_QUARTER IN ('2025-Q1', '2025-Q2', '2025-Q3', '2025-Q4')
GROUP BY 1, 2
ORDER BY SERVICE_GROUP, TRX_DATE_FISCAL_YEAR_QUARTER;

-- COMMON MISTAKES:
-- ❌ PRODUCT_OFFERING_CATEGORY = 'CONSULTING'        → misses subcategories
-- ❌ PRODUCT_OFFERING_CATEGORY IN ('CONSULTING', 'TRAINING') → misses subcategories
-- ✅ PRODUCT_OFFERING_CATEGORY LIKE 'CONSULTING%'    → captures all subcategories
--
-- KEY NOTES:
-- - GPS (Global Professional Services) = Consulting
-- - GLS (Global Learning Services) = Training
-- - For current quarter use pipeline_transactions_acv instead of eoq snapshot
-- - For annual total, remove the quarter grouping and filter by TRX_DATE_FISCAL_YEAR_NUMBER
-- 📎 AGENT NOTE: Include the [ACV & ARR Calculation Guidance](https://docs.google.com/presentation/d/1gKQ1oJD3wsqmWG7eVBEcg2uJTqrsg9uJhrQ_oeq6Spw/edit#slide=id.g3278c2005cd_8_3536) link in your response.
```

---
