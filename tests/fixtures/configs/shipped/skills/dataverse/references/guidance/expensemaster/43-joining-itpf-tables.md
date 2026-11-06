<!-- expensemaster · from 10-it-forecast-future-spend-apptio-tables-1.md -->
### Joining ITPF tables

When you need to combine base forecast data with labor, asset, or contract details, use these join patterns:

| Target Table | Join Columns |
|--------------|--------------|
| `ITPF_LABOR_FORECAST_DAILY` | `source_line_item_code = line_item_code` + `period_date` + `forecast_entry_month` |
| `ITPF_ASSET_FORECAST_DAILY` | `source_line_item_code = line_item_code` + `forecast_entry_month` (no period_date) |
| `ITPF_CONTRACT_FORECAST_W_DELEGATION` | `source_line_item_code = line_item_code` + `period_date` + `current_fy_plan_version` |

**Important Notes:**

- **Always use `source_line_item_code`** from the base table (not `line_item_code`) when joining to detail tables.
- **Asset joins don't include `period_date`** — asset attributes are constant across periods.
- **Use LEFT JOIN** — not all line items have labor/asset/contract details.
- **Joining to base tables**: When joining `ITPF_ASSET_FORECAST_DAILY`, `ITPF_CONTRACT_FORECAST_W_DELEGATION`, or `ITPF_LABOR_FORECAST_DAILY` to `ITPF_FORECAST_DAILY_CURRENT` or `ITPF_FORECAST_DAILY_MONTH_VARIANCE`, use `line_item_code` from the detail table as the join condition to `source_line_item_code` in the base table.
