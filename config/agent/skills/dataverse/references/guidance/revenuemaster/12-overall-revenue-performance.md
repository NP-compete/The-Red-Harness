<!-- revenuemaster · from 02-validated-query-templates-1.md -->
### Overall Revenue Performance

```sql
-- ============================================================================
-- Total Revenue for the Current Year (Closed Quarters Only)
-- ============================================================================
-- Business Question: "What is our total revenue this year?"
-- Important: For current year queries, include ONLY CLOSED quarters
-- Red Hat quarters: Q1 (Jan-Mar), Q2 (Apr-Jun), Q3 (Jul-Sep), Q4 (Oct-Dec)
-- Example: As of November 2025, only Q1-Q3 are closed; Q4 is still in progress
--
-- ⚠️ CRITICAL: This is OPERATIONAL revenue which EXCLUDES IBM contingencies
-- IBM contingencies (intercompany transactions, Cloud Pak splits, IBM revenue splits)
-- are NOT included in this data product. External revenue is not yet available.
-- ============================================================================

SELECT
    FYQ,
    SUM(reporting_accounted_amount_at_current_year_plan_rate) AS reported_revenue
FROM revenuemaster_db.marts.revenue_external
WHERE
    gl_date BETWEEN '2025-01-01' AND '2025-12-31'
    AND is_internal_use = 0 and is_intercompany = 0
GROUP BY FYQ
ORDER BY FYQ;

-- Key Notes:
-- - ⚠️ Revenue shown is OPERATIONAL revenue EXCLUDING IBM contingencies
-- - Uses date range filter for the calendar year
-- - Always exclude internal use revenue (is_internal_use = 0)
-- - Use reporting_accounted_amount_at_current_year_plan_rate for consistent currency
-- - Group by FYQ for quarterly breakdown
```

```sql
-- ============================================================================
-- Revenue for a Specific Quarter
-- ============================================================================
-- Business Question: "Show me the total revenue for the second quarter of this year"
-- ============================================================================

SELECT
    SUM(reporting_accounted_amount_at_current_year_plan_rate) AS q2_total_revenue
FROM revenuemaster_db.marts.revenue_external
WHERE
    is_internal_use = 0 and is_intercompany = 0
    AND FYQ = '2025-Q2';
```
