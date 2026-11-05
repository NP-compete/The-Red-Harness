<!-- expensemaster · from 02-critical-rules.md -->
### GL & OneStream

1. **Schema**: Same as Common — use `EXPENSEMASTER_DB.RHAI_MARTS` by default, but if both schemas are available use the GL/OneStream copy in `EXPENSEMASTER_DB.TEST_MARTS`.
2. **Current Month Actuals**: Incomplete until 2nd workday of following month due to accruals
3. **Period**: Same as Common — use `period_date`; do not use `period_name`.
4. **Amount Aggregation**: Always SUM the appropriate amount column when grouping — multiple rows exist per dimension. See **Amount columns (when to use which)** under Column Selection Guide.
5. **Default Time Period**: When no time period is specified, default to **current year** using `YEAR(period_date) = YEAR(CURRENT_DATE())`
6. **Account Column Order**: When filtering on account hierarchy, ALWAYS use this order in WHERE clause (highest level first):
   - **GL_SUB_LEDGER_AGGREGATE**: `(account_rollup ILIKE '%term%' OR account_parent_cd ILIKE '%term%' OR account_name ILIKE '%term%')`
   - **ONESTREAM tables**: `(parent_account ILIKE '%term%' OR account_hierarchy ILIKE '%term%' OR account_name ILIKE '%term%')`
   - ❌ WRONG: Starting with `account_name` (most granular) instead of highest level
7. **Filter Note**: ALWAYS include `_filter_note` as the FIRST column. The note must:
   1. State the filter applied.
   2. End with plan rate used: **"(amounts at plan rate at time of transaction)"** for `amount_usd`, or **"(amounts at current year plan rate)"** for `amount_usd_current_plan_year`. Every ExpenseMaster query that returns amounts must have this in `_filter_note`.
   3. Also state in your natural-language response to the user: *"All amounts in USD at plan rate (plan rate at time of transaction)."* when using `amount_usd`, or *"All amounts in USD at current year plan rate."* when using `amount_usd_current_plan_year`. Do not omit the plan-rate note from either the SQL or the response.
   4. For GL/OneStream outputs, `_filter_note` **MUST** append this exact RLS suffix (after the plan-rate text): **"(results may be restricted by row-level security (RLS) and include only the cost centers you are authorized to access)"**. If this suffix is missing, the SQL is not compliant with this guidance.
8. **Hierarchy REGEXP Word-Boundary Matching**: The `cost_center_hierarchy` column uses `|` as segment delimiter and `_` as word separator. **Never use bare `ILIKE '%<term>%'`** — it matches substrings (e.g., `%IT%` matches Benef**it**s). Use **REGEXP** for true word-boundary matching: `REGEXP_LIKE(cost_center_hierarchy, '(^|.*[|])' || '<term>' || '[_|].*')`. See [Hierarchy Matching Rule](#-critical-hierarchy-matching-rule-avoid-false-positives) section.
9. **Variance Queries**: Include `_filter_note` as first column and `matched_at` to show filter matches. Match aggregation level to the question: "groups/teams" → `cost_center_name`; "cost centers" → `cost_center_code`; "categories" → `parent_account`. Use `scenario = 'Plan'` for "budget", `scenario = 'Forecast_<Mon>'` for forecasts.
10. **Variance Query Column Rule**: In variance queries, only reference columns that exist in the CTE's SELECT/GROUP BY. If `matched_at` needs a column value, include that column in the CTE. Error `[SYS_VW.COLUMN_N] is not a valid group by expression` means you referenced a column not in the CTE output.
11. **LISTAGG is an Aggregate**: `LISTAGG` is an aggregate function like `SUM`. **NEVER put `LISTAGG` in GROUP BY**. Only include non-aggregate columns in `GROUP BY`.
12. **RLS-aware zero-result interpretation**: GL/OneStream results can be scoped by row-level access. If a GL/OneStream query returns zero rows (or zero total), do **not** conclude globally that there is no spend. Use: **"No spend data was returned for the cost centers you currently have access to for this query and period."**
