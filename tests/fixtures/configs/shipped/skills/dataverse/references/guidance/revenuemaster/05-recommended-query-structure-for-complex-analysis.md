<!-- revenuemaster · from 01-critical-table-volumes-query-performance.md -->
### Recommended Query Structure for Complex Analysis

```sql
-- TEMPLATE: Optimized multi-table revenue analysis
WITH
-- Step 1: Pre-filter each source table to target time period
gtm_filtered AS (
    SELECT arrangement_number, gl_date, fyq, geo, trx_split_region,
           adjusted_reporting_accounted_amount_at_current_year_plan_rate AS revenue
    FROM revenuemaster_db.marts.go_to_market_revenue
    WHERE gl_date >= '2025-01-01' AND gl_date < '2026-01-01'
      AND is_internal_use = 0
),
rbo_filtered AS (
    SELECT revenue_arrangement_number, revenue_gl_date, offering_group_hybrid_split,
           split_rev_current_year_plan_rate AS revenue
    FROM revenuemaster_db.marts.revenue_by_offering
    WHERE revenue_gl_date >= '2025-01-01' AND revenue_gl_date < '2026-01-01'
      AND revenue_is_internal_use = 0
      AND revenue_is_sub = 1
),

-- Step 2: Combine data sources using UNION ALL (not multi-way JOINs)
combined_revenue AS (
    SELECT gtm.geo, gtm.fyq, COALESCE(rbo.offering_group_hybrid_split, 'OTHER') AS product_line,
           COALESCE(rbo.revenue, gtm.revenue) AS revenue
    FROM gtm_filtered gtm
    LEFT JOIN rbo_filtered rbo
        ON gtm.arrangement_number = rbo.revenue_arrangement_number
        AND gtm.gl_date = rbo.revenue_gl_date
),

-- Step 3: Aggregate early to reduce row count
quarterly_summary AS (
    SELECT geo, fyq, product_line, SUM(revenue) AS quarterly_revenue
    FROM combined_revenue
    GROUP BY geo, fyq, product_line
    HAVING SUM(revenue) > 100000  -- Filter immaterial amounts early
)

-- Step 4: Apply window functions on smaller aggregated dataset
SELECT *,
    ROUND(100.0 * quarterly_revenue / SUM(quarterly_revenue) OVER (PARTITION BY fyq), 2) AS pct_of_total
FROM quarterly_summary
ORDER BY fyq, quarterly_revenue DESC;
```

---

## 🔴 Critical Rules (ALWAYS APPLY)

### 1. Currency Standards
- Use fields with `_at_current_year_plan_rate` suffix for consistent currency reporting
- For revenue foundation: `reporting_accounted_amount_at_current_year_plan_rate`
- For GTM revenue: `adjusted_reporting_accounted_amount_at_current_year_plan_rate`

### 2. Internal Use Exclusion
- **ALWAYS exclude** internal use revenue: `is_internal_use = 0` in WHERE clauses
- Internal use revenue should not be included in standard revenue reporting

### 3. Service and Subscription Flags
- Use `is_service` flag to filter service vs non-service revenue (1 = service, 0 = non-service)
- Use `is_sub` flag to identify subscription revenue (1 = subscription, 0 = non-subscription)

### 4. Fiscal Year Quarter Format
- Use `FYQ` field with format: 'YYYY-Q#' (e.g., '2025-Q2')
- Always include FYQ in GROUP BY for quarterly analysis

### 5. Current Year Revenue Queries
- When users ask for "current year" or "this year" revenue, include ONLY CLOSED quarters
- Red Hat quarters: Q1 (Jan-Mar), Q2 (Apr-Jun), Q3 (Jul-Sep), Q4 (Oct-Dec)
- A quarter is considered "closed" only after it has been completed
- Do NOT include the current ongoing quarter or future quarters
