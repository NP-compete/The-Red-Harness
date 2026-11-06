<!-- expensemaster · from 10-it-forecast-future-spend-apptio-tables-1.md -->
### Compensation & Benefits (C&B) Handling

> **CRITICAL**: C&B (Labor costs) are **NOT** included in future year forecasts (beyond current fiscal year).

**Key C&B Rules:**

- **Never say "costs dropped"** when C&B shows $0 in future years.
- **Always explain**: "C&B shows $0 because it isn't forecasted in future years, not due to cost savings."
- **Provide dual analysis** when comparing current year to future years:
  - **WITH C&B**: Shows all costs (reveals apparent reduction that's actually missing forecast data).
  - **WITHOUT C&B**: Excludes C&B from both periods (true operational cost comparison).
- **Monthly labor cost**: Do not use the `PERIOD_AMOUNT` column for salary; it only indicates if the person was employed. Use: `(SUM(base_compensation / 12)) / COUNT(DISTINCT period_date) AS monthly_cost`. Base_compensation gives the cost for the year; dividing by 12 gives monthly cost by row; dividing by COUNT(period_date) removes duplication.
- For labor extension impact and FTE counts, see the **ITPF_LABOR_FORECAST_DAILY** mart YAML (end_date, quantity, etc.).

**C&B Identification:**

- **Field**: `ACCOUNT_GROUP = 'C&B'` (e.g., "Wages Base")
- **Typical location**: Under "Internal Labor" cost pool
