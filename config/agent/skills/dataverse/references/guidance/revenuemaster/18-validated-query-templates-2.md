<!-- revenuemaster · from 03-validated-query-templates-2.md -->
ance?"
-- ============================================================================
-- KEY PERFORMANCE COMPONENTS (revenue_component_level_1):
-- 1. In Quarter Yield: New bookings/upsells recognized in current quarter (updates daily)
-- 2. Backdated: Backdated revenue adjustments from prior periods (updates daily)
-- 3. Operational CCSP/Services: Operational services revenue (updates daily)
-- 4. Firm: Contracted/baseline revenue (books mostly on day 1 of month)
--
-- These components update DAILY and should be tracked against forecast/target
--
-- ⚠️ CRITICAL: This is OPERATIONAL revenue which EXCLUDES IBM contingencies
-- IBM contingencies (intercompany transactions, Cloud Pak splits, IBM revenue splits)
-- are NOT included. Always state: "This is operational revenue excluding IBM contingencies"
-- ============================================================================

-- Current Quarter-to-Date by Key Performance Component
SELECT
    revenue_component_level_1,
    DATE_TRUNC('month', gl_date) AS revenue_month,
    SUM(reporting_accounted_amount_at_current_year_plan_rate) AS revenue_at_plan_rate,
    ROUND(100.0 * SUM(reporting_accounted_amount_at_current_year_plan_rate) /
          SUM(SUM(reporting_accounted_amount_at_current_year_plan_rate)) OVER (), 2) AS pct_of_qtd_total
FROM revenuemaster_db.marts.revenue_external
WHERE
    fyq = '2025-Q4'  -- Current quarter
    AND is_internal_use = 0
    AND revenue_component_level_1 IS NOT NULL
GROUP BY revenue_component_level_1, DATE_TRUNC('month', gl_date)
ORDER BY revenue_at_plan_rate DESC;

-- Key Notes:
-- - ⚠️ Revenue shown is OPERATIONAL revenue EXCLUDING IBM contingencies
-- - In Quarter Yield: Indicator of new sales momentum within quarter
-- - Backdated: Adjustments from catch-up bookings or corrections
-- - Operational CCSP: Variable services revenue (consulting, support)
-- - Firm: Baseline contracted revenue (predictable/recurring)
-- - Compare these components vs forecast/target to assess performance
```

```sql
-- ============================================================================
-- Business Question: "Show me daily trending for key revenue components this month"
-- ============================================================================
-- Tracks DAILY performance of key variable components
-- Use this to monitor day-over-day trends and identify anomalies
--
-- ⚠️ CRITICAL: This is OPERATIONAL revenue which EXCLUDES IBM contingencies
-- IBM contingencies (intercompany, Cloud Pak splits, IBM revenue splits) are NOT included
-- ============================================================================

SELECT
    DATE_TRUNC('day', gl_date) AS revenue_day,
    SUM(CASE WHEN revenue_component_level_1 = 'In Quarter Yield'
        THEN reporting_accounted_amount_at_current_year_plan_rate ELSE 0 END) AS in_quarter_yield,
    SUM(CASE WHEN revenue_component_level_1 = 'Backdated'
        THEN reporting_accounted_amount_at_current_year_plan_rate ELSE 0 END) AS backdated,
    SUM(CASE WHEN revenue_component_level_1 = 'Operational CCSP'
        THEN reporting_accounted_amount_at_current_year_plan_rate ELSE 0 END) AS services,
    SUM(CASE WHEN revenue_component_level_1 = 'Firm'
        THEN reporting_accounted_amount_at_current_year_plan_rate ELSE 0 END) AS firm_revenue,
    SUM(reporting_accounted_amount_at_current_year_plan_rate) AS total_external_revenue
FROM revenuemaster_db.marts.revenue_external
WHERE
    gl_date >= DATE_TRUNC('month', CURRENT_DATE)  -- Current month
    AND gl_date <= CURRENT_DATE  -- Through today
    AND is_internal_use = 0 AND is_intercompany = 0
GROUP BY DATE_TRUNC('day', gl_date)
ORDER BY revenue_day;

-- Key Insights:
-- - ⚠️ All revenue shown is OPERATIONAL revenue EXCLUDING IBM contingencies
-- - In Quarter Yield: Should grow steadily throughout quarter as new deals close
-- - Backdated: Lumpy/sporadic as backdated bookings are processed
-- - Operational Services: Updates with monthly/quarterly service billings
-- - Firm: Front-loads ~90% on day 1, minimal daily additions
```

```sql
-- ============================================================================
-- Business Question: "Compare QTD performance vs prior quarter"
-- ============================================================================
-- ⚠️ NOTE: Year-over-Year (YoY) comparisons are PREFERRED for performance analysis
-- This QoQ comparison is provided for reference but may be misleading due to seasonality
-- For meaningful performance insights, use the YoY comparison template below
--
-- Shows quarter-over-quarter comparison by key revenue components
-- Useful for "Are we trending better or worse than last quarter?"
--
-- IMPORTANT: If current quarter is incomplete, this comparison is directional only
-- For apples-to-apples QoQ: compare same # of days in both quarters (see YoY template)
-- ============================================================================

WITH date_context AS (
    SELECT
        CURRENT_DATE AS today,
        LAST_DAY(DATE_TRUNC('quarter', CURRENT_DATE)) AS current_quarter_end,
        CASE
            WHEN CURRENT_DATE < LAST_DAY(DATE_TRUNC('quarter', CURRENT_DATE))
            THEN 'INCOMPLETE'
            ELSE 'COMPLETE'
        END AS quarter_status
),

qtd_comparison AS (
    SELECT
        fyq,
        revenue_component_level_1,
        MAX(gl_date) AS last_data_date,
        SUM(reporting_accounted_amount_at_current_year_plan_rate) AS qtd_revenue
    FROM revenuemaster_db.marts.revenue_external
    WHERE
        fyq IN ('2025-Q4', '2025-Q3')  -- Current and prior quarter
        AND is_internal_use = 0 and is_intercompany = 0
        AND revenue_component_level_1 IN ('In Quarter Yield', 'Backdated', 'Operational CCSP', 'Firm')
    GROUP BY fyq, revenue_component_level_1
)
SELECT
    revenue_component_level_1,
    SUM(CASE WHEN fyq = '2025-Q3' THEN qtd_revenue ELSE 0 END) AS q3_revenue_complete,
    SUM(CASE WHEN fyq = '2025-Q4' THEN qtd_revenue ELSE 0 END) AS q4_revenue_qtd,
    MAX(CASE WHEN fyq = '2025-Q4' THEN last_data_date END) AS q4_last_date,
    ROUND(100.0 * (SUM(CASE WHEN fyq = '2025-Q4' THEN qtd_revenue ELSE 0 END) -
                    SUM(CASE WHEN fyq = '2025-Q3' THEN qtd_revenue ELSE 0 END)) /
          NULLIF(SUM(CASE WHEN fyq = '2025-Q3' THEN qtd_revenue ELSE 0 END), 0), 2) AS qoq_growth_pct,
    (SELECT quarter_status FROM date_context) AS comparison_note
FROM qtd_comparison
GROUP BY revenue_component_level_1
ORDER BY q4_revenue_qtd DESC;

-- Key Comparisons:
-- - In Quarter Yield growth: Indicates improving/declining new sales
-- - Backdated changes: Can signal booking quality or process issues
-- - Operational Services trends: Reflects services business health
-- - Firm baseline: Should be relatively stable QoQ
--
-- ⚠️ IMPORTANT: QoQ comparisons can be misleading due to seasonality
-- For meaningful performance analysis, use Year-over-Year (YoY) comparisons (see template below)
-- WARNING: If comparison_note = 'INCOMPLETE', Q4 is incomplete (comparing full Q3 vs partial Q4)
-- For true apples-to-apples: use YoY template logic with DATEADD to match same day counts
```
