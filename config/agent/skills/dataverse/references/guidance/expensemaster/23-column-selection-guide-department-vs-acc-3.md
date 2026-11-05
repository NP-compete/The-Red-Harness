<!-- expensemaster · from 06-column-selection-guide-department-vs-acc-3.md -->
_hierarchy, '(^|.*[|])' || '<ORG_TERM>' || '[_|].*')
                 THEN 'cost_center_hierarchy: ' || REGEXP_SUBSTR(cost_center_hierarchy, '[^|]*<ORG_TERM>[^|]*')
        END, ', '
    ) as matched_at_org,
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
  AND (cost_center_department = '<ORG_TERM>'
       OR REGEXP_LIKE(cost_center_hierarchy, '(^|.*[|])' || '<ORG_TERM>' || '[_|].*'))
  AND (account_rollup ILIKE '%<EXPENSE_TERM>%'
       OR account_parent_cd ILIKE '%<EXPENSE_TERM>%'
       OR account_name ILIKE '%<EXPENSE_TERM>%')
GROUP BY account_rollup, account_name
ORDER BY total_spend DESC;
```
