<!-- sfsales · from 02-advanced-analysis-patterns.md -->
### Competitive Analysis
```sql
-- Lost deal competitive analysis
SELECT
    o.main_competitor,
    o.closed_lost_reason,
    COUNT(DISTINCT o.opportunity_id) as lost_deals,
    SUM(o.opportunity_amount) as lost_revenue,
    AVG(o.opportunity_amount) as avg_lost_deal_size,
    COUNT(DISTINCT o.account_id) as unique_accounts_lost,
    ROUND(AVG(DATEDIFF('day', o.created_date, o.opportunity_close_date)), 2) as avg_sales_cycle_days
FROM sfsales_db.marts.opportunity o
WHERE o.is_deleted = false
  AND o.stage_name = 'Closed Lost'
  AND o.fiscal_year = 2025
  AND o.main_competitor IS NOT NULL
  AND o.opportunity_amount > 0
GROUP BY o.main_competitor, o.closed_lost_reason
HAVING COUNT(DISTINCT o.opportunity_id) >= 3  -- Minimum competitive losses for analysis
ORDER BY lost_revenue DESC;
```

## 📈 Business Intelligence Insights
