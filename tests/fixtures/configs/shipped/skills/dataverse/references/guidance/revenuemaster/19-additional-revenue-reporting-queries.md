<!-- revenuemaster · from 03-validated-query-templates-2.md -->
### Additional Revenue Reporting Queries

```sql
-- ============================================================================
-- Revenue for a Completed Fiscal Year
-- ============================================================================
-- Business Question: "Show me revenue for fiscal year 2024"
-- Note: Use this for COMPLETED years only (e.g., 2024, 2023)
-- For the CURRENT year, use the Year-to-Date query that includes only CLOSED quarters
-- ============================================================================

SELECT
    YEAR(gl_date) AS fiscal_year,
    SUM(reporting_accounted_amount_at_current_year_plan_rate) AS total_revenue
FROM revenuemaster_db.marts.revenue_foundation
WHERE
    YEAR(gl_date) = 2024
GROUP BY YEAR(gl_date);
```

```sql
-- ============================================================================
-- Current Quarter Revenue to Date
-- ============================================================================
-- Business Question: "What's our current quarter revenue to date?"
-- Shows revenue accumulated so far with date range
-- ============================================================================

SELECT
    FYQ,
    MIN(gl_date) AS quarter_start,
    MAX(gl_date) AS last_date_with_data,
    SUM(reporting_accounted_amount_at_current_year_plan_rate) AS revenue_to_date
FROM revenuemaster_db.marts.revenue_foundation
WHERE
    FYQ = '2025-Q3'  -- Current quarter
GROUP BY FYQ;
```
