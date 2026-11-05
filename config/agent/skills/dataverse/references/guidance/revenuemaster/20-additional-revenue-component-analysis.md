<!-- revenuemaster · from 03-validated-query-templates-2.md -->
### Additional Revenue Component Analysis

```sql
-- ============================================================================
-- Services vs Product Revenue Breakdown
-- ============================================================================
-- Business Question: "What's our services revenue vs product revenue?"
-- ============================================================================

SELECT
    FYQ,
    SUM(CASE WHEN is_service = 1 THEN reporting_accounted_amount_at_current_year_plan_rate ELSE 0 END) AS services_revenue,
    SUM(CASE WHEN is_service = 0 THEN reporting_accounted_amount_at_current_year_plan_rate ELSE 0 END) AS product_revenue,
    SUM(reporting_accounted_amount_at_current_year_plan_rate) AS total_revenue,
    ROUND(100.0 * SUM(CASE WHEN is_service = 1 THEN reporting_accounted_amount_at_current_year_plan_rate ELSE 0 END) /
          SUM(reporting_accounted_amount_at_current_year_plan_rate), 2) AS services_pct
FROM revenuemaster_db.marts.revenue_foundation
WHERE
    FYQ = '2025-Q2'
    AND is_internal_use = 0
GROUP BY FYQ;
```

```sql
-- ============================================================================
-- Revenue Component Breakdown
-- ============================================================================
-- Business Question: "Break down revenue by component levels"
-- Shows detailed component hierarchy with percentages
-- ============================================================================

SELECT
    revenue_component,
    revenue_component_level_1,
    revenue_component_level_2,
    SUM(reporting_accounted_amount_at_current_year_plan_rate) AS revenue,
    ROUND(100.0 * SUM(reporting_accounted_amount_at_current_year_plan_rate) /
          SUM(SUM(reporting_accounted_amount_at_current_year_plan_rate)) OVER(), 2) AS pct_of_total
FROM revenuemaster_db.marts.revenue_foundation
WHERE
    FYQ = '2025-Q2'
    AND revenue_component IS NOT NULL
GROUP BY revenue_component, revenue_component_level_1, revenue_component_level_2
ORDER BY revenue DESC
LIMIT 15;
```
