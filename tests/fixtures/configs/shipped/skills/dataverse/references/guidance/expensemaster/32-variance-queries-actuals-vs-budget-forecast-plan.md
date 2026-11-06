<!-- expensemaster · from 08-golden-query-templates-gl-onestream-1.md -->
### 7.2 Variance Queries (Actuals vs Budget/Forecast/Plan)

> **Before generating**: Translate aliases using [Common Aliases](#️-important-common-aliases-apply-to-all-queries) (e.g., "G&A" → `GnA`, "HR" → `People`, "T&E" → `Travel and Entertainment`, "PPL" → requires REGEXP pattern).

**Common Variance Questions:**
| Question | Pattern | Scenario |
|----------|---------|----------|
| What is total Sales spend in 2025 compared to budget? | Org + Period | `'Plan'` |
| How did total spend for PPL team in Q4 compare to BoQ forecast? | Org + Period | `'Forecast_Oct'` |
| What is the Nov 2025 forecast to actual variance for PnGE? | Org + Period | `'Forecast_Nov'` |
| Which Sales Groups overspent vs budget on T&E in 2025? | Org + Account + Period | `'Plan'` |

**Available Scenarios**: `'Plan'` (budget), `'Forecast_Jan'` through `'Forecast_Dec'`

#### ⚠️ Variance Query Rules (Avoid Common Errors)

| Rule | Why |
|------|-----|
| **SELECT only columns you GROUP BY in CTEs** | Final SELECT can only use columns from CTE output |
| **`matched_at` must use CTE columns** | If showing dynamic values like `cost_center_hierarchy`, include it in CTE SELECT/GROUP BY |
| **Include `cost_center_name` in CTE if needed** | Add to SELECT, GROUP BY, and use in final output |
| **Apply same filters to BOTH CTEs** | Actuals and Forecast CTEs must have matching WHERE clauses |

**Snowflake Error**: `[SYS_VW.COLUMN_N] is not a valid group by expression` → You referenced a column not in the CTE's SELECT/GROUP BY.

**`matched_at` guidance:**
- **Known Department (Pattern A)**: Use static string `'cost_center_department: Sales'` (department is known)
- **REGEXP match (Pattern B)**: Include `cost_center_hierarchy` in CTE, then use `'cost_center_hierarchy: ' || COALESCE(a.cost_center_hierarchy, f.cost_center_hierarchy)`

---

**Pattern A - Org + Period (Known Department):**
```sql
WITH actuals AS (
   SELECT cost_center_code, cost_center_name, SUM(amount_usd) AS act_amt
   FROM EXPENSEMASTER_DB.RHAI_MARTS.ONESTREAM_FINANCIAL_AGGREGATE
   WHERE scenario = 'Actual'
     AND period_date >= '<START_DATE>' AND period_date <= '<END_DATE>'
     AND cost_center_department = '<DEPARTMENT>'
   GROUP BY cost_center_code, cost_center_name
),
forecast AS (
   SELECT cost_center_code, cost_center_name, SUM(amount_usd) AS fcst_amt
   FROM EXPENSEMASTER_DB.RHAI_MARTS.ONESTREAM_FINANCIAL_AGGREGATE
   WHERE scenario = '<SCENARIO>'
     AND period_date >= '<START_DATE>' AND period_date <= '<END_DATE>'
     AND cost_center_department = '<DEPARTMENT>'
   GROUP BY cost_center_code, cost_center_name
)
SELECT
   'Filtered by: <DEPARTMENT>, <PERIOD> Actuals vs <SCENARIO> (amounts at plan rate at time of transaction)' AS _filter_note,
   'cost_center_department: <DEPARTMENT>' AS matched_at,
   COALESCE(a.cost_center_code, f.cost_center_code) AS cost_center_code,
   COALESCE(a.cost_center_name, f.cost_center_name) AS cost_center_name,
   COALESCE(a.act_amt, 0) AS actual_amount,
   COALESCE(f.fcst_amt, 0) AS forecast_amount,
   COALESCE(a.act_amt, 0) - COALESCE(f.fcst_amt, 0) AS variance,
   CASE WHEN COALESCE(a.act_amt, 0) > COALESCE(f.fcst_amt, 0) THEN 'Overage' ELSE 'Underage' END AS variance_type
FROM actuals a
FULL OUTER JOIN forecast f ON a.cost_center_code = f.cost_center_code
ORDER BY ABS(variance) DESC;
```

**Pattern B - Org + Period (NOT Known Department, e.g., PPL, IT, GnA):**

> **Note**: Include `cost_center_hierarchy` in CTE SELECT/GROUP BY so `matched_at` can show actual matched values.

```sql
WITH actuals AS (
   SELECT cost_center_code, cost_center_name, cost_center_hierarchy, SUM(amount_usd) AS act_amt
   FROM EXPENSEMASTER_DB.RHAI_MARTS.ONESTREAM_FINANCIAL_AGGREGATE
   WHERE scenario = 'Actual'
     AND period_date >= '<START_DATE>' AND period_date <= '<END_DATE>'
     AND (cost_center_department = '<DEPARTMENT>'
          OR REGEXP_LIKE(cost_center_hierarchy, '(^|.*[|])(<DEPARTMENT>)[_|].*'))
   GROUP BY cost_center_code, cost_center_name, cost_center_hierarchy
),
forecast AS (
   SELECT cost_center_code, cost_center_name, cost_center_hierarchy, SUM(amount_usd) AS fcst_amt
   FROM EXPENSEMASTER_DB.RHAI_MARTS.ONESTREAM_FINANCIAL_AGGREGATE
   WHERE scenario = '<SCENARIO>'
     AND period_date >= '<START_DATE>' AND period_date <= '<END_DATE>'
     AND (cost_center_department = '<DEPARTMENT>'
          OR REGEXP_LIKE(cost_center_hierarchy, '(^|.*[|])(<DEPARTMENT>)[_|].*'))
   GROUP BY cost_center_code, cost_center_name, cost_center_hierarchy
)
SELECT
   'Filtered by: <DEPARTMENT> org, <PERIOD> Actuals vs <SCENARIO> (amounts at plan rate at time of transaction)' AS _filter_note,
   'cost_center_hierarchy: ' || REGEXP_SUBSTR(COALESCE(a.cost_center_hierarchy, f.cost_center_hierarchy), '[^|]*<DEPARTMENT>[^|]*') AS matched_at,
   COALESCE(a.cost_center_code, f.cost_center_code) AS cost_center_code,
   COALESCE(a.cost_center_name, f.cost_center_name) AS cost_center_name,
   COALESCE(a.act_amt, 0) AS actual_amount,
   COALESCE(f.fcst_amt, 0) AS forecast_amount,
   COALESCE(a.act_amt, 0) - COALESCE(f.fcst_amt, 0) AS variance,
   CASE WHEN COALESCE(a.act_amt, 0) > COALESCE(f.fcst_amt, 0) THEN 'Overage' ELSE 'Underage' END AS variance_type
FROM actuals a
FULL OUTER JOIN forecast f ON a.cost_center_code = f.cost_center_code
ORDER BY ABS(variance) DESC;
```

**Pattern C - Org + Account + Period (e.g., "Sales T&E vs budget"):**
```sql
WITH actuals AS (
   SELECT cost_center_code, cost_center_name, cost_center_department, parent_account, SUM(amount_usd) AS act_amt
   FROM EXPENSEMASTER_DB.RHAI_MARTS.ONESTREAM_FINANCIAL_AGGREGATE
   WHERE scenario = 'Actual'
     AND period_date >= '<START_DATE>' AND period_date <= '<END_DATE>'
     AND cost_center_department = '<DEPARTMENT>'
     AND (parent_account ILIKE '%<ACCOUNT_TERM>%' OR account_name ILIKE '%<ACCOUNT_TERM>%')
   GROUP BY cost_center_code, cost_center_name, cost_center_department, parent_account
),
forecast AS (
   SELECT cost_center_code, cost_center_name, cost_center_department, parent_account, SUM(amount_usd) AS fcst_amt
   FROM EXPENSEMASTER_DB.RHAI_MARTS.ONESTREAM_FINANCIAL_AGGREGATE
   WHERE scenario = '<SCENARIO>'
     AND period_date >= '<START_DATE>' AND period_date <= '<END_DATE>'
     AND cost_center_department = '<DEPARTMENT>'
     AND (parent_account ILIKE '%<ACCOUNT_TERM>%' OR account_name ILIKE '%<ACCOUNT_TERM>%')
   GROUP BY cost_center_code, cost_center_name, cost_center_department, parent_account
)
SELECT
   'Filtered by: <DEPARTMENT> + <ACCOUNT_TERM>, <PERIOD> Actuals vs <SCENARIO> (amounts at plan rate at time of transaction)' AS _filter_note,
   'org: ' || COALESCE(a.cost_center_department, f.cost_center_department) || ', account: ' || COALESCE(a.parent_account, f.parent_account) AS matched_at,
   COALESCE(a.cost_center_code, f.cost_center_code) AS cost_center_code,
   COALESCE(a.cost_center_name, f.cost_center_name) AS cost_center_name,
   COALESCE(a.parent_account, f.parent_account) AS parent_account,
   COALESCE(a.act_amt, 0) AS actual_amount,
   COALESCE(f.fcst_amt, 0) AS forecast_amount,
   COALESCE(a.act_amt, 0) - COALESCE(f.fcst_amt, 0) AS variance
FROM actuals a
FULL OUTER JOIN forecast f ON a.cost_center_code = f.cost_center_code AND a.parent_account = f.parent_account
WHERE COALESCE(a.act_amt, 0) - COALESCE(f.fcst_amt, 0) > 0  -- overspent only
ORDER BY variance DESC;
```
