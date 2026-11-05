<!-- sfsales · from 01-business-context-domain.md -->
### Account Segmentation Analysis
```sql
SELECT
    a.account_segment,
    a.industry,
    a.billing_country,
    COUNT(DISTINCT a.account_id) as total_accounts,
    COUNT(DISTINCT o.opportunity_id) as total_opportunities,
    SUM(o.opportunity_amount) as total_opportunity_value,
    COUNT(DISTINCT CASE WHEN o.is_won = true THEN o.opportunity_id END) as won_opportunities,
    SUM(CASE WHEN o.is_won = true THEN o.opportunity_amount ELSE 0 END) as won_revenue,
    ROUND(SUM(o.opportunity_amount) / NULLIF(COUNT(DISTINCT a.account_id), 0), 2) as avg_opportunity_per_account,
    ROUND(COUNT(DISTINCT CASE WHEN o.is_won = true THEN o.opportunity_id END) * 100.0 /
          NULLIF(COUNT(DISTINCT o.opportunity_id), 0), 2) as segment_win_rate_pct
FROM sfsales_db.marts.account a
LEFT JOIN sfsales_db.marts.opportunity o ON a.account_id = o.account_id
WHERE a.is_deleted = false
  AND o.is_deleted = false
  AND o.fiscal_year = 2025
  AND a.account_segment IS NOT NULL
GROUP BY a.account_segment, a.industry, a.billing_country
HAVING COUNT(DISTINCT a.account_id) >= 10  -- Statistical significance threshold
ORDER BY total_opportunity_value DESC;
```
