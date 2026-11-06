<!-- sfsales · from 02-advanced-analysis-patterns.md -->
### Sales Cycle Analysis
```sql
-- Opportunity progression timing analysis
WITH opportunity_stages AS (
    SELECT
        oh.opportunity_id,
        oh.stage_name,
        oh.created_date as stage_entry_date,
        LEAD(oh.created_date) OVER (PARTITION BY oh.opportunity_id ORDER BY oh.created_date) as next_stage_date,
        o.opportunity_close_date,
        o.is_won
    FROM sfsales_db.marts.opportunity_history oh
    JOIN sfsales_db.marts.opportunity o ON oh.opportunity_id = o.opportunity_id
    WHERE oh.is_deleted = false
      AND o.is_deleted = false
      AND o.fiscal_year = 2025
),
stage_durations AS (
    SELECT
        opportunity_id,
        stage_name,
        DATEDIFF('day', stage_entry_date,
                 COALESCE(next_stage_date, opportunity_close_date)) as days_in_stage,
        is_won
    FROM opportunity_stages
    WHERE days_in_stage > 0
)
SELECT
    stage_name,
    COUNT(DISTINCT opportunity_id) as opportunities_in_stage,
    AVG(days_in_stage) as avg_days_in_stage,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY days_in_stage) as median_days_in_stage,
    COUNT(DISTINCT CASE WHEN is_won = true THEN opportunity_id END) as won_from_stage,
    ROUND(COUNT(DISTINCT CASE WHEN is_won = true THEN opportunity_id END) * 100.0 /
          NULLIF(COUNT(DISTINCT opportunity_id), 0), 2) as conversion_rate_pct
FROM stage_durations
GROUP BY stage_name
ORDER BY avg_days_in_stage;
```
