<!-- sfsales · from 01-business-context-domain.md -->
### Product Performance Analysis
```sql
SELECT
    p.product_name,
    p.product_family,
    p.product_code,
    COUNT(DISTINCT op.opportunity_id) as opportunities_with_product,
    SUM(op.quantity) as total_quantity_sold,
    SUM(op.total_price) as total_product_revenue,
    SUM(op.acv_opportunity_product) as total_product_acv,
    SUM(op.arr_opportunity_product) as total_product_arr,
    ROUND(SUM(op.total_price) / NULLIF(SUM(op.quantity), 0), 2) as avg_unit_price,
    COUNT(DISTINCT CASE WHEN o.is_won = true THEN op.opportunity_id END) as won_opportunities_with_product
FROM sfsales_db.marts.product p
JOIN sfsales_db.marts.opportunity_product op ON p.product_id = op.product_id
JOIN sfsales_db.marts.opportunity o ON op.opportunity_id = o.opportunity_id
WHERE p.is_deleted = false
  AND op.is_deleted = false
  AND o.is_deleted = false
  AND o.fiscal_year = 2025
  AND op.total_price > 0
GROUP BY p.product_name, p.product_family, p.product_code
HAVING COUNT(DISTINCT op.opportunity_id) >= 3  -- Minimum market presence
ORDER BY total_product_revenue DESC;
```

## 🔍 Business Domain Knowledge
