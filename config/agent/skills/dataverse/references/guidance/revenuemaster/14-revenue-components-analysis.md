<!-- revenuemaster · from 02-validated-query-templates-1.md -->
### Revenue Components Analysis

```sql
-- ============================================================================
-- Firm Revenue / Revenue Under Contract (Non-Service)
-- ============================================================================
-- Business Question: "What is our firm revenue or revenue under contract?"
-- Important: Filters for non-service revenue only (is_service = 0)
-- ============================================================================

SELECT
    source_system,
    revenue_component,
    revenue_component_level_3,
    fyq,
    SUM(reporting_accounted_amount_at_current_year_plan_rate) AS firm_revenue
FROM REVENUEMASTER_DB.MARTS.REVENUE_FOUNDATION_SNAPSHOT
WHERE
    YEAR(gl_date) = 2026
    AND is_service = 0  -- Non-service revenue only
    AND is_internal_use = 0  -- Exclude internal use
    AND snapshot_date::date = '2026-02-23"   -- picks only one snapshot date
GROUP BY 1, 2, 3, 4
ORDER BY fyq, source_system;
```
