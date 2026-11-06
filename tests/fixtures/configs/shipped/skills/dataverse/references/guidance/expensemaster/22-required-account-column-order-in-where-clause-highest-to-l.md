<!-- expensemaster · from 05-column-selection-guide-department-vs-acc-2.md -->
### ⚠️ REQUIRED: Account Column Order in WHERE Clause (Highest to Lowest)

When filtering on account hierarchy, **ALWAYS list columns in this EXACT order in the WHERE clause** (highest level first):

**GL_SUB_LEDGER_AGGREGATE:**
1. `account_rollup` (highest - e.g., "OpEx", "Compensation") - CHECK FIRST
2. `account_parent_cd` (mid-level - e.g., "Marketing Expense", "Software") - CHECK SECOND
3. `account_name` (most granular - e.g., "Computer Software Expense") - CHECK LAST

**ONESTREAM tables:**
1. `parent_account` (highest - e.g., "Total Comp and Benefits") - CHECK FIRST
2. `account_hierarchy` (mid-level - full hierarchy path) - CHECK SECOND
3. `account_name` (most granular - readable account name) - CHECK LAST

**CORRECT ORDER (GL):**
```sql
WHERE (account_rollup ILIKE '%term%' OR account_parent_cd ILIKE '%term%' OR account_name ILIKE '%term%')
```

**CORRECT ORDER (OneStream):**
```sql
WHERE (parent_account ILIKE '%term%' OR account_hierarchy ILIKE '%term%' OR account_name ILIKE '%term%')
```

**WRONG ORDER (do NOT use):**
```sql
-- Starting with account_name (most granular) instead of highest level
WHERE (account_name ILIKE '%term%' OR ...)
```

**Query Pattern for ORGANIZATIONAL:**

> **IMPORTANT:** First check if `<term>` matches a **Known Department** (see list above). If yes, use Pattern A. If no, use Pattern B.

**Pattern A - Known Department (exact match only):**
```sql
SELECT
    'Filtered by: cost_center_department = <term>' as _filter_note,
    'cost_center_department: <term>' as matched_at,
    account_rollup,
    SUM(amount_usd) as total_spend
FROM EXPENSEMASTER_DB.RHAI_MARTS.GL_SUB_LEDGER_AGGREGATE
WHERE YEAR(period_date) = YEAR(CURRENT_DATE())
  AND cost_center_department = '<term>'
GROUP BY account_rollup
ORDER BY total_spend DESC;
```

**Pattern B - NOT a Known Department (REGEXP word-boundary matching):**

> **⚠️ GROUP BY Rule**: `LISTAGG` is an aggregate function. Only include non-aggregate columns in `GROUP BY`. **NEVER put `LISTAGG` in GROUP BY.** If no breakdown needed, omit `GROUP BY` entirely.

```sql
-- Total spend (no breakdown) - NO GROUP BY needed
SELECT
    'Filtered by: cost_center_department = <term> or cost_center_hierarchy word-boundary <term>' as _filter_note,
    LISTAGG(DISTINCT
        CASE
            WHEN cost_center_department = '<term>' THEN 'cost_center_department: ' || cost_center_department
            WHEN REGEXP_LIKE(cost_center_hierarchy, '(^|.*[|])' || '<term>' || '[_|].*')
                 THEN 'cost_center_hierarchy: ' || REGEXP_SUBSTR(cost_center_hierarchy, '[^|]*<term>[^|]*')
        END, ', '
    ) as matched_at,
    SUM(amount_usd) as total_spend
FROM EXPENSEMASTER_DB.RHAI_MARTS.GL_SUB_LEDGER_AGGREGATE
WHERE YEAR(period_date) = YEAR(CURRENT_DATE())
  AND (cost_center_department = '<term>'
       OR REGEXP_LIKE(cost_center_hierarchy, '(^|.*[|])' || '<term>' || '[_|].*'));

-- Spend by account - GROUP BY only the breakdown column
SELECT
    'Filtered by: cost_center_department = <term> or cost_center_hierarchy word-boundary <term>' as _filter_note,
    LISTAGG(DISTINCT
        CASE
            WHEN cost_center_department = '<term>' THEN 'cost_center_department: ' || cost_center_department
            WHEN REGEXP_LIKE(cost_center_hierarchy, '(^|.*[|])' || '<term>' || '[_|].*')
                 THEN 'cost_center_hierarchy: ' || REGEXP_SUBSTR(cost_center_hierarchy, '[^|]*<term>[^|]*')
        END, ', '
    ) as matched_at,
    account_rollup,
    SUM(amount_usd) as total_spend
FROM EXPENSEMASTER_DB.RHAI_MARTS.GL_SUB_LEDGER_AGGREGATE
WHERE YEAR(period_date) = YEAR(CURRENT_DATE())
  AND (cost_center_department = '<term>'
       OR REGEXP_LIKE(cost_center_hierarchy, '(^|.*[|])' || '<term>' || '[_|].*'))
GROUP BY account_rollup  -- Only non-aggregate columns here, NOT LISTAGG
ORDER BY total_spend DESC;
```

**Query Pattern for ACCOUNT:**
```sql
SELECT
    'Searched for [<term>] in account_rollup, account_parent_cd, account_name' as _filter_note,
    LISTAGG(DISTINCT
        CASE
            WHEN account_rollup ILIKE '%<term>%' THEN 'account_rollup: ' || account_rollup
            WHEN account_parent_cd ILIKE '%<term>%' THEN 'account_parent_cd: ' || account_parent_cd
            WHEN account_name ILIKE '%<term>%' THEN 'account_name: ' || account_name
        END, ', '
    ) as matched_at,
    account_rollup,
    account_name,
    SUM(amount_usd) as total_spend
FROM EXPENSEMASTER_DB.RHAI_MARTS.GL_SUB_LEDGER_AGGREGATE
WHERE YEAR(period_date) = YEAR(CURRENT_DATE())
  AND (account_rollup ILIKE '%<term>%'
       OR account_parent_cd ILIKE '%<term>%'
       OR account_name ILIKE '%<term>%')
GROUP BY account_rollup, account_name
ORDER BY total_spend DESC;
```

**Combined Pattern (expense type within an org):**

> **IMPORTANT:** First check if `<ORG_TERM>` matches a **Known Department**. If yes, use Pattern A. If no, use Pattern B.

**Pattern A - Known Department:**
```sql
SELECT
    'Filtered by: cost_center_department = <ORG_TERM> AND account_rollup/account_parent_cd/account_name contains [<EXPENSE_TERM>]' as _filter_note,
    'cost_center_department: <ORG_TERM>' as matched_at_org,
    LISTAGG(DISTINCT
        CASE
            WHEN account_rollup ILIKE '%<EXPENSE_TERM>%' THEN 'account_rollup: ' || account_rollup
            WHEN account_parent_cd ILIKE '%<EXPENSE_TERM>%' THEN 'account_parent_cd: ' || account_parent_cd
            WHEN account_name ILIKE '%<EXPENSE_TERM>%' THEN 'account_name: ' || account_name
        END, ', '
    ) as matched_at_account,
    account_rollup,
    account_name,
    SUM(amount_usd) as total_spend
FROM EXPENSEMASTER_DB.RHAI_MARTS.GL_SUB_LEDGER_AGGREGATE
WHERE YEAR(period_date) = YEAR(CURRENT_DATE())
  AND cost_center_department = '<ORG_TERM>'
  AND (account_rollup ILIKE '%<EXPENSE_TERM>%'
       OR account_parent_cd ILIKE '%<EXPENSE_TERM>%'
       OR account_name ILIKE '%<EXPENSE_TERM>%')
GROUP BY account_rollup, account_name
ORDER BY total_spend DESC;
```

**Pattern B - NOT a Known Department (REGEXP word-boundary matching):**
```sql
SELECT
    'Filtered by: cost_center_department = <ORG_TERM> or cost_center_hierarchy word-boundary <ORG_TERM> AND account contains [<EXPENSE_TERM>]' as _filter_note,
    LISTAGG(DISTINCT
        CASE
            WHEN cost_center_department = '<ORG_TERM>' THEN 'cost_center_department: ' || cost_center_department
            WHEN REGEXP_LIKE(cost_center
