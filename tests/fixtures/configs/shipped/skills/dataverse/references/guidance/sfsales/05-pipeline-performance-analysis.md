<!-- sfsales · from 01-business-context-domain.md -->
### Pipeline Performance Analysis
```sql
SELECT
    o.fiscal_quarter,
    o.fiscal_year,
    o.stage_name,
    o.forecast_category,
    COUNT(DISTINCT o.opportunity_id) as opportunity_count,
    SUM(o.opportunity_amount) as total_pipeline_value,
    SUM(o.acv_opportunity_amount) as total_acv,
    SUM(o.arr_opportunity_amount) as total_arr,
    AVG(o.probability) as avg_probability,
    ROUND(SUM(o.opportunity_amount * o.probability / 100), 2) as weighted_pipeline
FROM sfsales_db.marts.opportunity o
WHERE o.is_deleted = false
  AND o.fiscal_year = 2025
  AND o.opportunity_amount > 0
GROUP BY o.fiscal_quarter, o.fiscal_year, o.stage_name, o.forecast_category
ORDER BY o.fiscal_quarter, total_pipeline_value DESC;
```
