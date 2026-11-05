<!-- revenuemaster · from 04-validated-query-templates-3.md -->
### Revenue Runrate Analysis

```sql
-- ============================================================================
-- Business Question: "What is our current revenue runrate?" (As of today)
-- ============================================================================
-- CRITICAL CONTEXT: Revenue is HIGHLY front-loaded at start of month
-- - ~90% of monthly revenue books on the 1st day of the month
-- - ~15-18% additional adjustment on last day of month
-- - This is firm/contracted revenue that recurs monthly
--
-- RUNRATE CALCULATION METHOD:
-- - CURRENT MONTH (incomplete): Exclude firm revenue, project OTHER revenue only
-- - COMPLETED MONTHS: Use actual total revenue (include firm + other)
--
-- Logic:
-- 1. Check if CURRENT_DATE is in the current month being analyzed
-- 2. If YES (incomplete month): EXCLUDE firm revenue from runrate calculation
-- 3. If NO (completed month): INCLUDE all revenue in calculation
-- ============================================================================

-- Step 1: Determine if we're analyzing current month or a completed month
WITH month_context AS (
    SELECT
        DATE_TRUNC('month', CURRENT_DATE) AS current_month_start,
        CURRENT_DATE AS today
),

-- Step 2: Get month-to-date or full month revenue breakdown
monthly_revenue AS (
    SELECT
        DATE_TRUNC('month', gl_date) AS revenue_month,
        DATE_TRUNC('day', gl_date) AS revenue_day,
        -- For CURRENT month: separate firm vs other
        -- For COMPLETED months: use total
        SUM(CASE
            WHEN DATE_TRUNC('month', gl_date) = (SELECT current_month_start FROM month_context)
                 AND (is_firm_quarterly = 0 AND is_firm_annually = 0)
            THEN reporting_accounted_amount_at_current_year_plan_rate
            WHEN DATE_TRUNC('month', gl_date) < (SELECT current_month_start FROM month_context)
            THEN reporting_accounted_amount_at_current_year_plan_rate
            ELSE 0
        END) AS runrate_revenue_daily,
        SUM(CASE
