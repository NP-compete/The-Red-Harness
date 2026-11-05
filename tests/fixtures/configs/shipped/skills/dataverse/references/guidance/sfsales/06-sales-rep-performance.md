<!-- sfsales · from 01-business-context-domain.md -->
### Sales Rep Performance
```sql
SELECT
    u.user_full_name as sales_rep,
    u.title,
    t.territory_name,
    COUNT(DISTINCT o.opportunity_id) as opportunities_managed,
    SUM(CASE WHEN o.is_won = true THEN o.opportunity_amount ELSE 0 END) as closed_won_revenue,
    SUM(CASE WHEN o.stage_name NOT IN ('Closed Won', 'Closed Lost') THEN o.opportunity_amount ELSE 0 END) as open_pipeline,
    ROUND(SUM(CASE WHEN o.is_won = true THEN o.opportunity_amount ELSE 0 END) /
          NULLIF(COUNT(DISTINCT CASE WHEN o.is_closed = true THEN o.opportunity_id END), 0), 2) as avg_deal_size,
    ROUND(COUNT(DISTINCT CASE WHEN o.is_won = true THEN o.opportunity_id END) * 100.0 /
          NULLIF(COUNT(DISTINCT CASE WHEN o.is_closed = true THEN o.opportunity_id END), 0), 2) as win_rate_pct
FROM sfsales_db.marts.user u
LEFT JOIN sfsales_db.marts.territory t ON u.user_id = t.territory_owner_id
LEFT JOIN sfsales_db.marts.opportunity o ON u.user_id = o.owner_id
WHERE u.is_active = true
  AND o.is_deleted = false
  AND o.fiscal_year = 2025
GROUP BY u.user_full_name, u.title, t.territory_name
HAVING COUNT(DISTINCT o.opportunity_id) >= 5  -- Minimum activity threshold
ORDER BY closed_won_revenue DESC;
```
