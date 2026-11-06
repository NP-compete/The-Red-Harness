<!-- revenuemaster · from 01-critical-table-volumes-query-performance.md -->
## 🎯 Available Data Tables

| Table | Purpose | Key Columns | Notes |
|-------|---------|-------------|-------|
| `MARTS.REVENUE_FOUNDATION` | Core revenue data with GL and source system details | gl_date, FYQ, source_system, revenue_component, **revenue_component_level_1**, revenue_component_level_3, is_service, is_sub, is_internal_use, reporting_accounted_amount_at_current_year_plan_rate | Primary table for revenue analysis |

| `MARTS.REVENUE_FOUNDATION_FPA_ADJUSTMENTS` |  Operational revenue with finance team manual adjustments, accruals, and reclassifications applied | Same as REVENUE_FOUNDATION + **revenue_component_level_1** (In Quarter Yield, Backdated, Operational CCSP, Firm) | Use for QTD performance tracking and when finance adjustments are needed |
| `MARTS.REVENUE_EXTERNAL` |  External revenue with finance team manual adjustments, accruals, and reclassifications applied | Same as REVENUE_FOUNDATION + **revenue_component_level_1** (In Quarter Yield, Backdated, Operational CCSP, Firm) | Use for QTD performance tracking and when finance adjustments are needed |
| `MARTS.GO_TO_MARKET_REVENUE` | Revenue data enriched with GTM attributes | gl_date, FYQ, geo, trx_split_region, adjusted_reporting_accounted_amount_at_current_year_plan_rate | Use for geo and region-level analysis |

| `MARTS.REVENUE_BY_OFFERING` | Revenue by product offering | offering_group_hybrid_split, revenue_gl_date, revenue_fyq, split_rev_current_year_plan_rate, split_rev_actual_rate, revenue_is_internal_use, revenue_is_sub | Use for product-level revenue analysis |
