<!-- revenuemaster · from 02-validated-query-templates-1.md -->
### Revenue by Customer Analysis

```sql
-- ============================================================================
-- Revenue by Customer (Including Services))
-- ============================================================================
-- Business Question: "What is the revenue for Servicenow in 2025?"
-- Important: Refer to sold to customer name
-- ============================================================================

SELECT
    source_system,
    revenue_component,
    revenue_component_level_3,
    fyq,
    sold_to_customer_name,
    SUM(reporting_accounted_amount_at_current_year_plan_rate) AS revenue_at_planrate
FROM REVENUEMASTER_DB.MARTS.REVENUE_EXTERNAL
WHERE
    YEAR(gl_date) = 2025
    --AND is_service = 0  -- Non-service revenue only
    AND is_internal_use = 0  -- Exclude internal use
    AND sold_to_customer_name ilike '%Servicenow%'
GROUP BY 1, 2, 3, 4,5
ORDER BY fyq, source_system;
```
