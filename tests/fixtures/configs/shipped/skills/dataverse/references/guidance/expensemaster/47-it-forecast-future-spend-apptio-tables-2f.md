<!-- expensemaster · from 11-it-forecast-future-spend-apptio-tables-2.md -->
#### 8.8 Service / application TCO (TBM tables)

**Question**: What is the YTD spend for the Computers service? (Use `SERVICE_COST_BY_TOWER_MONTHLY` or `SERVICE_COST_BY_COST_POOL_MONTHLY`; no forecast filter. Always SUM(`cost`) — multiple rows per service.)

```sql
SELECT
    MAX('Using Apptio data, which includes spend that resides in IT cost centers.') AS _filter_note,
    service_name,
    SUM(cost) AS total_cost
FROM EXPENSEMASTER_DB.RHAI_MARTS.SERVICE_COST_BY_TOWER_MONTHLY
WHERE service_name ILIKE '%Computers%'
  AND month_date BETWEEN DATE_TRUNC('year', CURRENT_DATE()) AND CURRENT_DATE()
GROUP BY service_name;
```

**Question**: How much compute spend is associated with application ANSI-001? (Use `APP_SPEND_BY_TOWER_MONTHLY`; filter by application name and optionally `it_resource_tower_name` for a specific tower like Compute.)

```sql
SELECT
    MAX('Using Apptio data, which includes spend that resides in IT cost centers.') AS _filter_note,
    month_date,
    application_name,
    it_resource_tower_name,
    SUM(cost) AS tower_cost
FROM EXPENSEMASTER_DB.RHAI_MARTS.APP_SPEND_BY_TOWER_MONTHLY
WHERE application_id ILIKE '%ANSI-001%'
  AND it_resource_tower_name ILIKE '%Compute%'
GROUP BY month_date,application_name, it_resource_tower_name;
```
