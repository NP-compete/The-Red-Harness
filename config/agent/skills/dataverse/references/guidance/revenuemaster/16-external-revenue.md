<!-- revenuemaster · from 02-validated-query-templates-1.md -->
### External Revenue
```sql
-- ============================================================================
-- External Revenue with CloudPak and Revsplits from IBM (Including Services))
-- ============================================================================
-- Business Question: "What is the total revenue in 2025"
-- Important: Exclude intercompany revenue and include revenue from source system 'divrt'
-- ============================================================================
SELECT
    source_system,
    revenue_component,
    revenue_component_level_3,
    fyq,
    SUM(reporting_accounted_amount_at_current_year_plan_rate) AS revenue_at_planrate
FROM REVENUEMASTER_DB.MARTS.REVENUE_EXTERNAL
WHERE
    YEAR(gl_date) = 2025
    --AND is_service = 0  -- Non-service revenue only
    AND is_internal_use = 0  -- Exclude internal use
    AND is_intercompany = 0 -- Exclude intercompany revenue
GROUP BY 1, 2, 3, 4
ORDER BY fyq, source_system;
```

```sql
-- ============================================================================
-- Subscription Revenue Analysis
-- ============================================================================
-- Business Question: "What is our subscriptions revenue in Q2'25?"
-- Important: Filters for subscription revenue only (is_sub = 1)
-- ============================================================================

SELECT
    source_system,
    revenue_component,
    revenue_component_level_3,
    fyq,
    SUM(reporting_accounted_amount_at_current_year_plan_rate) AS subscription_revenue
FROM REVENUEMASTER_DB.MARTS.REVENUE_EXTERNAL
WHERE
    YEAR(gl_date) = 2026
    AND is_sub = 1  -- Subscription revenue only
    AND is_internal_use = 0  -- Exclude internal use
    AND is_intercompany = 0 --Exclude intercompany revenue from Subs
GROUP BY 1, 2, 3, 4
ORDER BY fyq, source_system;
```

```sql
-- ============================================================================
-- Services Revenue Analysis
-- ============================================================================
-- Business Question: "What is services revenue in Q2'25?"
-- Important: Excludes both non-service and internal use revenue
-- ============================================================================

SELECT
    fyq,
    SUM(reporting_accounted_amount_at_current_year_plan_rate) AS services_revenue
FROM REVENUEMASTER_DB.MARTS.REVENUE_EXTERNAL
WHERE
    fyq = '2025-Q2'
    AND is_service = 1      -- Filter for service revenue
    AND is_internal_use = 0 -- Exclude internal use
    AND is_intercompany = 0 --Exclude intercompany services
GROUP BY 1;
```
