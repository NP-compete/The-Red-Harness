<!-- revenuemaster · from 05-validated-query-templates-4.md -->
WHEN is_firm_quarterly = 1 OR is_firm_annually = 1
            THEN reporting_accounted_amount_at_current_year_plan_rate
            ELSE 0
        END) AS firm_revenue_daily,
        SUM(reporting_accounted_amount_at_current_year_plan_rate) AS total_revenue_daily,
        MAX(CASE
            WHEN DATE_TRUNC('month', gl_date) = (SELECT current_month_start FROM month_context)
            THEN 1 ELSE 0
        END) AS is_current_month
    FROM revenuemaster_db.marts.revenue_foundation
    CROSS JOIN month_context
    WHERE
        -- Analyze current month through today, or full completed month
        gl_date >= DATE_TRUNC('month', CURRENT_DATE)
        AND gl_date <= CURRENT_DATE
        AND is_internal_use = 0
    GROUP BY DATE_TRUNC('month', gl_date), DATE_TRUNC('day', gl_date)
),

-- Step 3: Calculate monthly summary
revenue_summary AS (
    SELECT
        revenue_month,
        MAX(is_current_month) AS is_current_month,
        COUNT(DISTINCT revenue_day) AS days_with_data,
        SUM(runrate_revenue_daily) AS runrate_revenue_total,
        SUM(firm_revenue_daily) AS firm_revenue_total,
        SUM(total_revenue_daily) AS total_revenue,
        AVG(runrate_revenue_daily) AS avg_daily_runrate_revenue
    FROM monthly_revenue
    GROUP BY revenue_month
)

-- Step 4: Calculate annual runrate
SELECT
    TO_CHAR(revenue_month, 'YYYY-MM') AS analysis_month,
    CASE WHEN is_current_month = 1 THEN 'CURRENT (Incomplete)' ELSE 'COMPLETED' END AS month_status,
    days_with_data,
    runrate_revenue_total AS revenue_for_runrate_calc,
    firm_revenue_total,
    total_revenue,
    avg_daily_runrate_revenue,
    ROUND(avg_daily_runrate_revenue * 365, 2) AS annualized_runrate,
    CASE
        WHEN is_current_month = 1
        THEN 'Excludes firm revenue (projected from OTHER revenue only)'
        ELSE 'Includes all revenue (month completed)'
    END AS calculation_method,
    ROUND(100.0 * runrate_revenue_total / NULLIF(total_revenue, 0), 2) AS pct_used_for_runrate
FROM revenue_summary;

-- Key Notes:
-- - CURRENT month (incomplete): Runrate uses ONLY other revenue (excludes firm)
-- - COMPLETED months: Runrate uses ALL revenue (includes firm + other)
-- - Use CURRENT_DATE to determine if month is complete
-- - December 1st typically contains 90%+ of monthly firm revenue
-- - Other revenue accumulates more linearly throughout the month
```

```sql
-- ============================================================================
-- Business Question: "Show me the revenue booking pattern for this month"
-- ============================================================================
-- Validates the front-loading pattern: most revenue books on day 1
-- ============================================================================

SELECT
    DATE_TRUNC('day', gl_date) AS revenue_day,
    SUM(CASE
        WHEN is_firm_quarterly = 0 AND is_firm_annually = 0
        THEN reporting_accounted_amount_at_current_year_plan_rate
        ELSE 0
    END) AS other_revenue,
    SUM(CASE
        WHEN is_firm_quarterly = 1 OR is_firm_annually = 1
        THEN reporting_accounted_amount_at_current_year_plan_rate
        ELSE 0
    END) AS firm_revenue,
    SUM(reporting_accounted_amount_at_current_year_plan_rate) AS total_revenue,
    ROUND(100.0 * SUM(reporting_accounted_amount_at_current_year_plan_rate) /
          SUM(SUM(reporting_accounted_amount_at_current_year_plan_rate)) OVER (), 2) AS pct_of_mtd
FROM revenuemaster_db.marts.revenue_foundation
WHERE
    gl_date >= DATE_TRUNC('month', CURRENT_DATE)  -- Current month start
    AND gl_date <= CURRENT_DATE  -- Through today
    AND is_internal_use = 0
GROUP BY DATE_TRUNC('day', gl_date)
ORDER BY revenue_day;

-- Expected Pattern (based on historical data):
-- Day 1: ~90% of monthly revenue (mostly firm/contracted)
-- Days 2-30: ~10% distributed (mostly other/variable revenue)
-- Last day: ~15-18% adjustment (period-end true-ups)
```


```sql
--  Revenue by accounting geo (specify everytime that this is based on accounting geo and not Sales geo):
--Use Region as Geo
-- Location code is the country code. Use location code and location code name for accounting country level reporting


select
sum(reporting_accounted_amount_at_current_year_plan_rate) as revenue_at_plan_rate,
sum(reporting_accounted_amount_at_actual_rate) as atspotrate,
revenue_component_level_1,
is_sub,
calendar_year_number,
calendar_quarter_number,
calendar_month_number,
location_code,
company_code,
region,
source_system,
is_intercompany
from REVENUEMASTER_DB.MARTS.REVENUE_FOUNDATION_FPA_ADJUSTMENTS where
calendar_year_number > 2022 and is_internal_use = 0
group by all;

-- ============================================================================
-- Business Question: "Compare runrate across recent months"
-- ============================================================================
-- Shows runrate trends month-over-month
-- CURRENT month: Uses OTHER revenue only (excludes firm)
-- COMPLETED months: Uses TOTAL revenue (includes firm + other)
-- ============================================================================

WITH month_context AS (
    SELECT DATE_TRUNC('month', CURRENT_DATE) AS current_month_start
),

monthly_breakdown AS (
    SELECT
        DATE_TRUNC('month', gl_date) AS revenue_month,
        -- For CURRENT month: use OTHER revenue
        -- For COMPLETED months: use TOTAL revenue
        SUM(CASE
            WHEN DATE_TRUNC('month', gl_date) = (SELECT current_month_start FROM month_context)
                 AND (is_firm_quarterly = 0 AND is_firm_annually = 0)
            THEN reporting_accounted_amount_at_current_year_plan_rate
            WHEN DATE_TRUNC('month', gl_date) < (SELECT current_month_start FROM month_context)
            THEN reporting_accounted_amount_at_current_year_plan_rate
            ELSE 0
        END) AS runrate_revenue,
        SUM(CASE
            WHEN is_firm_quarterly = 0 AND is_firm_annually = 0
            THEN reporting_accounted_amount_at_current_year_plan_rate
            ELSE 0
        END) AS other_revenue,
        SUM(CASE
            WHEN is_firm_quarterly = 1 OR is_firm_annually = 1
            THEN reporting_accounted_amount_at_current_year_plan_rate
            ELSE 0
        END) AS firm_revenue,
        SUM(reporting_accounted_amount_at_current_year_plan_rate) AS total_revenue,
        MAX(CASE
            WHEN DATE_TRUNC('month', gl_date) = (SELECT current_month_start FROM month_context)
            THEN 1 ELSE 0
        END) AS is_current_month
    FROM revenuemaster_db.marts.revenue_foundation
    CROSS JOIN month_context
    WHERE
        gl_date >= '2025-10-01'
        AND (
            -- Include full completed months
            DATE_TRUNC('month', gl_date) < (SELECT current_month_start FROM month_context)
            -- Include current month through today only
            OR (DATE_TRUNC('month', gl_date) = (SELECT current_month_start FROM month_context)
                AND gl_date <= CURRENT_DATE)
        )
        AND is_internal_use = 0
    GROUP BY DATE_TRUNC('month', gl_date)
)
SELECT
    TO_CHAR(revenue_month, 'YYYY-MM') AS month,
    CASE WHEN is_current_month = 1 THEN 'CURRENT' ELSE 'COMPLETED' END AS status,
    runrate_revenue,
    other_revenue,
    firm_revenue,
    total_revenue,
    ROUND(runrate_revenue * 12, 2) AS annualized_runrate,
    CASE
        WHEN is_current_month = 1 THEN 'From OTHER revenue only'
        ELSE 'From TOTAL revenue'
    END AS runrate_basis,
    ROUND(100.0 * runrate_revenue / NULLIF(total_revenue, 0), 2) AS pct_used_for_runrate,
    ROUND(100.0 * (runrate_revenue - LAG(runrate_revenue) OVER (ORDER BY revenue_month)) /
          NULLIF(LAG(runrate_revenue) OVER (ORDER BY revenue_month), 0), 2) AS mom_runrate_growth
FROM monthly_breakdown
ORDER BY revenue_month DESC;

-- Key Notes:
-- - CURRENT month runrate = (monthly_other_revenue * 12)
-- - COMPLETED month runrate = (monthly_total_revenue * 12)
-- - Track month-over-month growth for trends
-- - CURRENT_DATE determines which month is incomplete
```

---
