<!-- bookingsmaster · from 02-critical-business-rules-always-apply-1.md -->
### 4b. Country-Level Reporting: Use `trx_country_of_order` and Always Include `trx_split_geo`

**CRITICAL**: When users ask for ACV+, ACV, or ARR **by country**, use `trx_country_of_order` (country name) and **always** include `trx_split_geo` in SELECT/GROUP BY so that the Telco geo portion is visible alongside other geos for the same country.

```sql
-- ✅ CORRECT - Country breakdown with geo visibility
SELECT trx_split_geo, trx_country_of_order, SUM(acv_plus_amount_usd_cy_pr) AS total_acv_plus_usd
FROM BOOKINGSMASTER_DB.MARTS.pipeline_transactions_acv
WHERE bookings_flag = 'Y' AND trx_crm_forecast_category <> 'Omitted'
GROUP BY trx_split_geo, trx_country_of_order
ORDER BY trx_country_of_order, trx_split_geo;
```

---
