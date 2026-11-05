<!-- revenuemaster · from 04-validated-query-templates-3.md -->
### Revenue Under Contract for Future Quarters

```sql
-- ============================================================================
-- Business Question: "Tell me the revenue under contract for the next two quarters"
-- ============================================================================
-- Shows firm/contracted revenue vs total revenue for future quarters
-- Uses is_firm_quarterly and is_firm_annually flags
-- ============================================================================

SELECT
    FYQ,
    SUM(CASE
        WHEN (is_firm_quarterly = 1 OR is_firm_annually = 1)
        THEN reporting_accounted_amount_at_current_year_plan_rate
        ELSE 0
    END) AS revenue_under_contract,
    SUM(reporting_accounted_amount_at_current_year_plan_rate) AS total_revenue,
    ROUND(100.0 * SUM(CASE
        WHEN (is_firm_quarterly = 1 OR is_firm_annually = 1)
        THEN reporting_accounted_amount_at_current_year_plan_rate
        ELSE 0
    END) / SUM(reporting_accounted_amount_at_current_year_plan_rate), 2) AS pct_under_contract
FROM revenuemaster_db.marts.revenue_foundation
WHERE
    FYQ IN ('2025-Q4', '2026-Q1')  -- Next two quarters
GROUP BY FYQ
ORDER BY FYQ;
```

```sql
-- Fall plan revenue at plan rate
-- Specify that this is plan evrytime when this query has been used
-- Use this table for yearly revenue performance comparisions

select revenue_component,
fiscal_year_quarter,
sum(revenue_usd_cypr) as revenue_at_plan_rate
from REVENUEMASTER_DB.FORECASTING_MARTS.CORE_GLOBAL_REVENUE_PLAN_CY26
group by all;
```

```sql
-- Forecast query from the Forecast tables
-- Always use the BOQ (Begining of Quarter) Metric case while doing the quarterly compare.
-- Use monthly Metric Case forecast for the monthly compare
--BOQ Metrics is based on the snapshot date which should be the 1st month of the quarter
-- For Yearly comparisons use the REVENUEMASTER_DB.FORECASTING_MARTS.CORE_GLOBAL_REVENUE_PLAN_CY26
-- Always show the Metric Case as a default forecast unless specified to pull the Execution Case or Mid Case.
-- Always pick the max(snapshot_date) from the REVENUEMASTER_DB.FORECASTING_MARTS.CORE_GLOBAL_REVENUE_FORECAST for a particular month.

select
sum(revenue_cypr) as revenue_at_plan_rate,
sum(revenue_spot_rate) as revenue_at_spot_rate,
revenue_component,
forecast_scenario,
fiscal_month_year
from REVENUEMASTER_DB.FORECASTING_MARTS.CORE_GLOBAL_REVENUE_FORECAST
where forecast_scenario = 'Metric Case'
group by all;
