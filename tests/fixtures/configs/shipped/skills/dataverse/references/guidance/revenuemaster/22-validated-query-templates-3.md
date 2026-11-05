<!-- revenuemaster · from 04-validated-query-templates-3.md -->
pare Dec 1-17, 2025 with Dec 1-17, 2024
-- - If Q4 2025 is incomplete through Dec 17, compare Oct 1-Dec 17 for both years
--
-- ⚠️ CRITICAL: This is OPERATIONAL revenue which EXCLUDES IBM contingencies
-- IBM contingencies (intercompany transactions, Cloud Pak splits, IBM revenue splits)
-- are NOT included in this data product. External revenue is not yet available.
-- Always state: "This is operational revenue excluding IBM contingencies"
-- ============================================================================

WITH date_context AS (
    SELECT
        CURRENT_DATE AS today,
        DATE_TRUNC('quarter', CURRENT_DATE) AS current_quarter_start,
        DATE_TRUNC('year', CURRENT_DATE) AS current_year_start,
        -- Calculate same date last year
        DATEADD(year, -1, CURRENT_DATE) AS same_date_last_year,
        DATEADD(year, -1, DATE_TRUNC('quarter', CURRENT_DATE)) AS prior_year_quarter_start
),

-- Current year revenue through today
current_year_revenue AS (
    SELECT
        'Current Year' AS period,
        YEAR(gl_date) AS year,
        QUARTER(gl_date) AS quarter,
        MIN(gl_date) AS start_date,
        MAX(gl_date) AS end_date,
        SUM(reporting_accounted_amount_at_current_year_plan_rate) AS revenue
    FROM revenuemaster_db.marts.revenue_foundation
    CROSS JOIN date_context
    WHERE
        gl_date >= date_context.current_quarter_start  -- Start of current quarter
        AND gl_date <= date_context.today  -- Through today
        AND is_internal_use = 0
    GROUP BY YEAR(gl_date), QUARTER(gl_date)
),

-- Prior year revenue for SAME DATE RANGE (apples-to-apples)
prior_year_revenue AS (
    SELECT
        'Prior Year' AS period,
        YEAR(gl_date) AS year,
        QUARTER(gl_date) AS quarter,
        MIN(gl_date) AS start_date,
        MAX(gl_date) AS end_date,
        SUM(reporting_accounted_amount_at_current_year_plan_rate) AS revenue
    FROM revenuemaster_db.marts.revenue_foundation
    CROSS JOIN date_context
    WHERE
        gl_date >= date_context.prior_year_quarter_start  -- Same quarter start, prior year
        AND gl_date <= date_context.same_date_last_year  -- SAME DATE last year (apples-to-apples)
        AND is_internal_use = 0
    GROUP BY YEAR(gl_date), QUARTER(gl_date)
)

-- Combine and calculate YoY growth
SELECT
    cy.year AS current_year,
    cy.quarter AS current_quarter,
    cy.start_date AS current_period_start,
    cy.end_date AS current_period_end,
    cy.revenue AS current_year_operational_revenue_excl_ibm,
    py.year AS prior_year,
    py.start_date AS prior_period_start,
    py.end_date AS prior_period_end,
    py.revenue AS prior_year_operational_revenue_excl_ibm,
    ROUND(cy.revenue - py.revenue, 2) AS revenue_change,
    ROUND(100.0 * (cy.revenue - py.revenue) / NULLIF(py.revenue, 0), 2) AS yoy_growth_pct,
    CASE
        WHEN cy.end_date < LAST_DAY(DATE_TRUNC('quarter', cy.end_date))
        THEN 'INCOMPLETE QUARTER - Apples-to-apples comparison through ' || TO_CHAR(cy.end_date, 'YYYY-MM-DD')
        ELSE 'COMPLETE QUARTER'
    END AS comparison_note,
    'OPERATIONAL REVENUE - Excludes IBM contingencies (intercompany, Cloud Pak splits, IBM revenue splits)' AS revenue_type_disclaimer
FROM current_year_revenue cy
CROSS JOIN prior_year_revenue py;

-- Key Notes:
-- - ⚠️ Revenue shown is OPERATIONAL revenue EXCLUDING IBM contingencies
-- - ALWAYS compares same date ranges (e.g., Dec 1-17 vs Dec 1-17 last year)
-- - Uses CURRENT_DATE to automatically match dates
-- - Clearly indicates if comparison is for incomplete period
-- - NO hardcoded dates - fully dynamic
-- - revenue_type_disclaimer column ensures IBM exclusion is always visible
```

```sql
-- ============================================================================
-- Eight Quarter Revenue Trend with Year-over-Year Growth
-- ============================================================================
-- Business Question: "What's the revenue trend for the last 8 quarters?"
--
-- 🎯 **PREFERRED**: Shows Year-over-Year (YoY) growth rates for each quarter
-- YoY growth is more meaningful than QoQ as it accounts for seasonality
-- Also includes QoQ growth for reference (can be misleading due to seasonality)
-- ============================================================================

WITH quarterly_revenue AS (
    SELECT
        FYQ,
        EXTRACT(YEAR FROM TO_DATE(SPLIT_PART(FYQ, '-', 1) || '-' ||
            CASE SPLIT_PART(FYQ, '-', 2)
                WHEN 'Q1' THEN '01-01'
                WHEN 'Q2' THEN '04-01'
                WHEN 'Q3' THEN '07-01'
                WHEN 'Q4' THEN '10-01'
            END, 'YYYY-MM-DD')) AS fiscal_year,
        SPLIT_PART(FYQ, '-', 2) AS quarter,
        SUM(reporting_accounted_amount_at_current_year_plan_rate) AS quarterly_revenue
    FROM revenuemaster_db.marts.revenue_foundation
    WHERE
        FYQ IN ('2025-Q3', '2025-Q2', '2025-Q1', '2024-Q4',
                '2024-Q3', '2024-Q2', '2024-Q1', '2023-Q4')
    GROUP BY FYQ
)
SELECT
    qr.FYQ,
    qr.quarterly_revenue,
    -- Year-over-Year growth (PREFERRED - accounts for seasonality)
    ROUND(100.0 * (qr.quarterly_revenue -
          LAG(qr.quarterly_revenue, 4) OVER (ORDER BY qr.FYQ)) /
          NULLIF(LAG(qr.quarterly_revenue, 4) OVER (ORDER BY qr.FYQ), 0), 2) AS yoy_growth_pct,
    -- Quarter-over-Quarter growth (for reference - can be misleading)
    ROUND(100.0 * (qr.quarterly_revenue -
          LAG(qr.quarterly_revenue, 1) OVER (ORDER BY qr.FYQ)) /
          NULLIF(LAG(qr.quarterly_revenue, 1) OVER (ORDER BY qr.FYQ), 0), 2) AS qoq_growth_pct
FROM quarterly_revenue qr
ORDER BY qr.FYQ DESC;

-- Key Notes:
-- - ⭐ YoY growth is PREFERRED for performance analysis (accounts for seasonality)
-- - QoQ growth is included for reference but can be misleading due to seasonal patterns
-- - YoY compares same quarter across years (e.g., Q4 2025 vs Q4 2024)
-- - QoQ compares consecutive quarters (e.g., Q4 2025 vs Q3 2025)
```
