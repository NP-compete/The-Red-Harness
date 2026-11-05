<!-- expensemaster · from 06-column-selection-guide-department-vs-acc-3.md -->
### Query Patterns for ONESTREAM Tables

**Query Pattern for ORGANIZATIONAL (ONESTREAM):**

> **IMPORTANT:** First check if `<term>` matches a **Known Department**. If yes, use Pattern A. If no, use Pattern B.

**Pattern A - Known Department:**
```sql
SELECT
    'Filtered by: cost_center_department = <term>' as _filter_note,
    'cost_center_department: <term>' as matched_at,
    parent_account,
    SUM(amount_usd) as total_spend
FROM EXPENSEMASTER_DB.RHAI_MARTS.ONESTREAM_FINANCIAL_AGGREGATE
WHERE scenario = 'Actual'
  AND YEAR(period_date) = YEAR(CURRENT_DATE())
  AND cost_center_department = '<term>'
GROUP BY parent_account
ORDER BY total_spend DESC;
```

**Pattern B - NOT a Known Department (REGEXP word-boundary matching):**
```sql
SELECT
    'Filtered by: cost_center_department = <term> or cost_center_hierarchy word-boundary <term>' as _filter_note,
    LISTAGG(DISTINCT
        CASE
            WHEN cost_center_department = '<term>' THEN 'cost_center_department: ' || cost_center_department
            WHEN REGEXP_LIKE(cost_center_hierarchy, '(^|.*[|])' || '<term>' || '[_|].*')
                 THEN 'cost_center_hierarchy: ' || REGEXP_SUBSTR(cost_center_hierarchy, '[^|]*<term>[^|]*')
        END, ', '
    ) as matched_at,
    parent_account,
    SUM(amount_usd) as total_spend
FROM EXPENSEMASTER_DB.RHAI_MARTS.ONESTREAM_FINANCIAL_AGGREGATE
WHERE scenario = 'Actual'
  AND YEAR(period_date) = YEAR(CURRENT_DATE())
  AND (cost_center_department = '<term>'
       OR REGEXP_LIKE(cost_center_hierarchy, '(^|.*[|])' || '<term>' || '[_|].*'))
GROUP BY parent_account
ORDER BY total_spend DESC;
```

**Query Pattern for ACCOUNT (ONESTREAM):**
```sql
SELECT
    'Searched for [<term>] in parent_account, account_hierarchy, account_name' as _filter_note,
    LISTAGG(DISTINCT
        CASE
            WHEN parent_account ILIKE '%<term>%' THEN 'parent_account: ' || parent_account
            WHEN account_hierarchy ILIKE '%<term>%' THEN 'account_hierarchy: ' || account_hierarchy
            WHEN account_name ILIKE '%<term>%' THEN 'account_name: ' || account_name
        END, ', '
    ) as matched_at,
    parent_account,
    account_name,
    SUM(amount_usd) as total_spend
FROM EXPENSEMASTER_DB.RHAI_MARTS.ONESTREAM_FINANCIAL_AGGREGATE
WHERE scenario = 'Actual'
  AND YEAR(period_date) = YEAR(CURRENT_DATE())
  AND (parent_account ILIKE '%<term>%'
       OR account_hierarchy ILIKE '%<term>%'
       OR account_name ILIKE '%<term>%')
GROUP BY parent_account, account_name
ORDER BY total_spend DESC;
```

**Combined Pattern for ONESTREAM (expense type within an org):**

> **IMPORTANT:** First check if `<ORG_TERM>` matches a **Known Department**. If yes, use Pattern A. If no, use Pattern B.

**Pattern A - Known Department:**
```sql
SELECT
    'Filtered by: cost_center_department = <ORG_TERM> AND parent_account/account_hierarchy/account_name contains [<EXPENSE_TERM>]' as _filter_note,
    'cost_center_department: <ORG_TERM>' as matched_at_org,
    LISTAGG(DISTINCT
        CASE
            WHEN parent_account ILIKE '%<EXPENSE_TERM>%' THEN 'parent_account: ' || parent_account
            WHEN account_hierarchy ILIKE '%<EXPENSE_TERM>%' THEN 'account_hierarchy: ' || account_hierarchy
            WHEN account_name ILIKE '%<EXPENSE_TERM>%' THEN 'account_name: ' || account_name
        END, ', '
    ) as matched_at_account,
    parent_account,
    account_name,
    SUM(amount_usd) as total_spend
FROM EXPENSEMASTER_DB.RHAI_MARTS.ONESTREAM_FINANCIAL_AGGREGATE
WHERE scenario = 'Actual'
  AND YEAR(period_date) = YEAR(CURRENT_DATE())
  AND cost_center_department = '<ORG_TERM>'
  AND (parent_account ILIKE '%<EXPENSE_TERM>%'
       OR account_hierarchy ILIKE '%<EXPENSE_TERM>%'
       OR account_name ILIKE '%<EXPENSE_TERM>%')
GROUP BY parent_account, account_name
ORDER BY total_spend DESC;
```

**Pattern B - NOT a Known Department (REGEXP word-boundary matching):**
```sql
SELECT
    'Filtered by: cost_center_department = <ORG_TERM> or cost_center_hierarchy word-boundary <ORG_TERM> AND account contains [<EXPENSE_TERM>]' as _filter_note,
    LISTAGG(DISTINCT
        CASE
            WHEN cost_center_department = '<ORG_TERM>' THEN 'cost_center_department: ' || cost_center_department
            WHEN REGEXP_LIKE(cost_center_hierarchy, '(^|.*[|])' || '<ORG_TERM>' || '[_|].*')
                 THEN 'cost_center_hierarchy: ' || REGEXP_SUBSTR(cost_center_hierarchy, '[^|]*<ORG_TERM>[^|]*')
        END, ', '
    ) as matched_at_org,
    LISTAGG(DISTINCT
        CASE
            WHEN parent_account ILIKE '%<EXPENSE_TERM>%' THEN 'parent_account: ' || parent_account
            WHEN account_hierarchy ILIKE '%<EXPENSE_TERM>%' THEN 'account_hierarchy: ' || account_hierarchy
            WHEN account_name ILIKE '%<EXPENSE_TERM>%' THEN 'account_name: ' || account_name
        END, ', '
    ) as matched_at_account,
    parent_account,
    account_name,
    SUM(amount_usd) as total_spend
FROM EXPENSEMASTER_DB.RHAI_MARTS.ONESTREAM_FINANCIAL_AGGREGATE
WHERE scenario = 'Actual'
  AND YEAR(period_date) = YEAR(CURRENT_DATE())
  AND (cost_center_department = '<ORG_TERM>'
       OR REGEXP_LIKE(cost_center_hierarchy, '(^|.*[|])' || '<ORG_TERM>' || '[_|].*'))
  AND (parent_account ILIKE '%<EXPENSE_TERM>%'
       OR account_hierarchy ILIKE '%<EXPENSE_TERM>%'
       OR account_name ILIKE '%<EXPENSE_TERM>%')
GROUP BY parent_account, account_name
ORDER BY total_spend DESC;
```

---

**Variance Queries (Actuals vs Forecast):** For variance query patterns with complete examples, see [Section 7.2](#72-what-is-the-variance-between-actuals-and-a-forecast).
