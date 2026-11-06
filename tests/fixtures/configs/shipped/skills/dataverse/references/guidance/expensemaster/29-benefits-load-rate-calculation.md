<!-- expensemaster · from 07-business-definitions-logic-gl-onestream.md -->
### Benefits Load Rate Calculation

**Business Question**: "How does the 2025 Q4 Benefits Load Rate for Sales compare to the 2024 Q4 Benefits Load Rate?"

Use **`ONESTREAM_FINANCIAL_AGGREGATE`** with the account code mapping above. Use **`amount_usd`** (default) unless the user explicitly asks for "current plan rate", "use the current plan rate", or "current year plan rate", in which case use **`amount_usd_current_plan_year`**. Aggregate by `YEAR(period_date)` (or by period as needed), then compute load rate and optional year-over-year variance (e.g. `LAG(...) OVER (ORDER BY fiscal_year)` for change vs prior year). **Always include `_filter_note` as the first column** ending with **(amounts at plan rate at time of transaction)** or **(amounts at current year plan rate)** so the user sees which rate is used.

**Example query** (department, quarter, and years parameterized). Uses **`amount_usd`** (default); if user asked for "current plan rate" or "use the current plan rate", use `amount_usd_current_plan_year` and set `_filter_note` to end with "(amounts at current year plan rate)".

```sql
WITH metrics AS (
    SELECT
        YEAR(period_date) AS fiscal_year,
        SUM(CASE
            WHEN account_code IN ('SGA_601000', 'COR_601000')
            THEN amount_usd ELSE 0 END) AS total_wages,
        SUM(CASE
            WHEN account_code IN (
                'SGA_602000', 'SGA_604000', 'SGA_601500', 'SGA_OthLoadRate',
                'COR_602000', 'COR_604000', 'COR_601500', 'COR_OthLoadRate'
            ) THEN amount_usd ELSE 0 END) AS total_benefits
    FROM EXPENSEMASTER_DB.RHAI_MARTS.ONESTREAM_FINANCIAL_AGGREGATE
    WHERE cost_center_department = 'Sales'
      AND QUARTER(period_date) = 4
      AND YEAR(period_date) IN (2024, 2025)
      AND scenario = 'Actual'
    GROUP BY YEAR(period_date)
)
SELECT
    'Benefits Load Rate comparison for Sales Q4 (amounts at plan rate at time of transaction)' AS _filter_note,
    fiscal_year,
    total_wages,
    total_benefits,
    ROUND((total_benefits / NULLIF(total_wages, 0)) * 100, 2) AS benefits_load_rate_pct,
    ROUND(
        (total_benefits / NULLIF(total_wages, 0)) * 100 -
        LAG((total_benefits / NULLIF(total_wages, 0)) * 100) OVER (ORDER BY fiscal_year),
    2) AS bps_change_vs_py
FROM metrics
ORDER BY fiscal_year DESC;
```

**Key Points**:
- **Wages** for load rate: only `SGA_601000`, `COR_601000`.
- **Benefits** for load rate: Employee Tax, Benefits, Wages Vacation, Other Load Rate (all SGA/COR codes listed above).
- **Load Rate = (Total Benefits / Total Wages) × 100**; use `NULLIF` to prevent division by zero.
- **Amount column**: Default `amount_usd`; use `amount_usd_current_plan_year` only when user asks for "current plan rate", "use the current plan rate", or "current year plan rate".
- **`_filter_note`**: Always include as the FIRST column. End with **(amounts at plan rate at time of transaction)** when using `amount_usd`, or **(amounts at current year plan rate)** when using `amount_usd_current_plan_year`—so the response always shows which rate is used.
- For variance vs prior year, use `LAG(...) OVER (ORDER BY fiscal_year)` and optionally convert to basis points.
- Filter by `cost_center_department`, `QUARTER(period_date)`, `YEAR(period_date)`, and `scenario = 'Actual'` as required by the question.
