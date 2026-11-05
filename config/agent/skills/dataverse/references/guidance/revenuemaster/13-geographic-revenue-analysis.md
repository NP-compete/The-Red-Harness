<!-- revenuemaster · from 02-validated-query-templates-1.md -->
### Geographic Revenue Analysis

```sql
-- ============================================================================
-- Revenue by Geography by Quarter
-- ============================================================================
-- Business Question: "What is our revenue by geo by quarter in the last two years?"
-- Important: Uses GO_TO_MARKET_REVENUE table for geo attributes
--
-- ⚠️ CRITICAL: This is OPERATIONAL revenue which EXCLUDES IBM contingencies
-- ============================================================================

SELECT
    geo,
    FYQ,
    SUM(adjusted_reporting_accounted_amount_at_current_year_plan_rate) AS geo_operational_revenue_excl_ibm,
    'OPERATIONAL REVENUE - Excludes IBM contingencies' AS revenue_disclaimer
FROM revenuemaster_db.marts.GO_TO_MARKET_REVENUE
WHERE
    gl_date BETWEEN '2023-01-01' AND '2025-12-31'
    AND is_internal_use = 0
GROUP BY FYQ, geo
ORDER BY FYQ, geo;

-- Key Notes:
-- - ⚠️ Revenue shown is OPERATIONAL revenue EXCLUDING IBM contingencies
-- - GO_TO_MARKET_REVENUE table contains geo dimensions
-- - Use adjusted_reporting_accounted_amount_at_current_year_plan_rate for GTM table
```

```sql
-- ============================================================================
-- Revenue by Region by Quarter
-- ============================================================================
-- Business Question: "What is our revenue by region by quarter in the last two years?"
-- Important: Uses GO_TO_MARKET_REVENUE table for region-level detail (geo + region)
-- ============================================================================

SELECT
    fyq,
    CASE
        WHEN geo = 'ALLIANCES_ALLIANCES' THEN 'Alliances'
        ELSE geo
    END AS geo,
    CASE
        WHEN geo = 'IBM Internal' THEN 'IBM Internal'
        ELSE trx_split_region
    END AS the_region,
    SUM(adjusted_reporting_accounted_amount_at_current_year_plan_rate) AS revenue
FROM revenuemaster_db.marts.go_to_market_revenue
WHERE
    fyq BETWEEN '2023-Q1' AND '2025-Q4'
GROUP BY ALL
ORDER BY 1, 2, 3;

-- Key Notes:
-- - Uses GO_TO_MARKET_REVENUE for region-level breakdown
-- - Handles special cases for Alliances and IBM Internal geo naming
-- - Region field (trx_split_region) provides sub-geo level detail
```
