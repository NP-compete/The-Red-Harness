<!-- revenuemaster · from 02-validated-query-templates-1.md -->
### Product Revenue Performance

```sql
-- ============================================================================
-- Revenue by Product by Quarter and Month
-- ============================================================================
-- Business Question: "What is revenue by product by year by month?"
-- Important: Combines subscription offerings, services, and specific products (NOKIA)
-- ============================================================================

-- Subscription revenue by offering
SELECT
    offering_group_hybrid_split,
    revenue_fyq,
    YEAR(revenue_gl_date) AS calendar_year_number,
    MONTH(revenue_gl_date) AS calendar_month_number,
    SUM(split_rev_current_year_plan_rate) AS hybrid_rev_plan,
    SUM(split_rev_actual_rate) AS hybrid_rev_sr
FROM REVENUEMASTER_DB.MARTS.REVENUE_BY_OFFERING
WHERE
    YEAR(revenue_gl_date) = 2025
    AND revenue_is_internal_use = false
    AND revenue_is_sub = 1
    AND EXTRACT(QUARTER FROM revenue_gl_date) = 3
GROUP BY ALL

UNION ALL

-- Services revenue
SELECT
    'SERVICES' AS offering_group_hybrid_split,
    fyq,
    YEAR(gl_date) AS calendar_year_number,
    MONTH(gl_date) AS calendar_month_number,
    SUM(reporting_accounted_amount_at_current_year_plan_rate) AS hybrid_rev_plan,
    SUM(reporting_accounted_amount_at_actual_rate) AS hybrid_rev_sr
FROM REVENUEMASTER_DB.MARTS.REVENUE_EXTERNAL
WHERE
    YEAR(gl_date) = 2025
    AND is_internal_use = false
    AND is_service = 1
    AND is_intercompany = 0
    AND EXTRACT(QUARTER FROM gl_date) = 3
GROUP BY ALL

UNION ALL

-- NOKIA specific products
SELECT
    'NOKIA' AS offering_group_hybrid_split,
    fyq,
    YEAR(gl_date) AS calendar_year_number,
    MONTH(gl_date) AS calendar_month_number,
    SUM(reporting_accounted_amount_at_current_year_plan_rate) AS hybrid_rev_plan,
    SUM(reporting_accounted_amount_at_actual_rate) AS hybrid_rev_sr
FROM REVENUEMASTER_DB.MARTS.REVENUE_EXTERNAL
WHERE
    YEAR(gl_date) = 2025
    AND is_internal_use = false
    AND is_intercompany = 0
    AND gl_product_id IN ('804','805','806','807')
    AND EXTRACT(QUARTER FROM gl_date) = 3
GROUP BY ALL;

-- Key Notes:
-- - Combines three data sources: REVENUE_BY_OFFERING, REVENUE_FOUNDATION_FPA_ADJUSTMENTS
-- - Services and NOKIA products come from FPA_ADJUSTMENTS table
-- - Subscription offerings come from REVENUE_BY_OFFERING table
```

### QTD Performance & Daily Trending Analysis

```sql
-- ============================================================================
-- Business Question: "How are we doing this quarter?" / "What's our QTD perform
