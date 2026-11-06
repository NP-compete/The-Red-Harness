<!-- revenuemaster · from 04-validated-query-templates-3.md -->
### Revenue Linearity Analysis

```sql
-- ============================================================================
-- Business Question: "Describe our linearity over the last 4 quarters"
-- ============================================================================
-- Shows monthly revenue distribution within each quarter to analyze linearity
-- Perfect linearity would be 33.33% each month
-- ============================================================================

SELECT
    FYQ,
    DATE_TRUNC('month', gl_date) AS revenue_month,
    SUM(reporting_accounted_amount_at_current_year_plan_rate) AS monthly_revenue,
    ROUND(100.0 * SUM(reporting_accounted_amount_at_current_year_plan_rate) /
          SUM(SUM(reporting_accounted_amount_at_current_year_plan_rate)) OVER (PARTITION BY FYQ), 2) AS pct_of_quarter
FROM revenuemaster_db.marts.revenue_foundation
WHERE
    FYQ IN ('2025-Q2', '2025-Q1', '2024-Q4', '2024-Q3')
GROUP BY FYQ, DATE_TRUNC('month', gl_date)
ORDER BY FYQ DESC, revenue_month;
```
