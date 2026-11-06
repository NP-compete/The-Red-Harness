<!-- bookingsmaster · from 10-common-mistakes-to-avoid.md -->
### 3. Use CTEs for Readability

For complex queries, use CTEs to break down logic:

```sql
WITH current_quarter_bookings AS (
    SELECT
        trx_split_geo,
        product_split_offering_group,
        SUM(acv_plus_amount_usd_cy_pr) as total_acv_plus
    FROM pipeline_transactions_acv
    WHERE bookings_flag = 'Y'
      AND trx_crm_forecast_category <> 'Omitted'
      AND TRX_DATE_FISCAL_YEAR_QUARTER = TO_CHAR(CURRENT_DATE, 'YYYY') || '-Q' || TO_CHAR(CEIL(EXTRACT(MONTH FROM CURRENT_DATE) / 3))
    GROUP BY 1, 2
)
SELECT * FROM current_quarter_bookings
WHERE total_acv_plus > 1000000  -- Focus on $1M+ products
ORDER BY total_acv_plus DESC;
```

### 4. Validate Results

Before presenting results:
- Check if numbers are in expected range
- Verify geography totals make sense
- Confirm forecast categories are valid
- Watch for unexpectedly high NULL counts

### 5. Handle NULLs Appropriately

```sql
-- For product analysis, NULL often means Discover stage
SELECT
    COALESCE(product_split_offering_group, 'Discover Stage / No Product') as product,
    SUM(acv_plus_amount_usd_cy_pr) as total_acv_plus
FROM pipeline_transactions_acv
WHERE bookings_flag = 'Y'
GROUP BY 1;
```

---
