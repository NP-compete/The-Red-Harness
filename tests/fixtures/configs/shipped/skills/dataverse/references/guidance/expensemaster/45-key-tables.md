<!-- expensemaster · from 10-it-forecast-future-spend-apptio-tables-1.md -->
### Key tables

- **ITPF:** `ITPF_FORECAST_DAILY_CURRENT`, `ITPF_CONTRACT_FORECAST_W_DELEGATION`, `ITPF_LABOR_FORECAST_DAILY`, `ITPF_ASSET_FORECAST_DAILY`, `ITPF_FORECAST_DAILY_MONTH_VARIANCE`. Each has a version filter and table-specific rules in its dbt mart YAML.
- **TBM (OpEx; no forecast filter):** `APP_SPEND_BY_TOWER_MONTHLY`, `APP_SPEND_BY_COST_POOL_MONTHLY`, `SERVICE_COST_BY_TOWER_MONTHLY`, `SERVICE_COST_BY_COST_POOL_MONTHLY`. Multiple rows per app/service; aggregation and usage → mart YAML.

Table choice and per-table CRITICAL rules → dbt mart descriptions (USE THIS TABLE WHEN / DO NOT USE WHEN / CRITICAL).
