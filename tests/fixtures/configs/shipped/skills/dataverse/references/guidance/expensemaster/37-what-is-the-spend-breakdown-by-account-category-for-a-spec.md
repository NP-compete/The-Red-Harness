<!-- expensemaster · from 09-golden-query-templates-gl-onestream-2.md -->
### 7.6 What is the spend breakdown by account category for a specific cost center?

**Parameters**: Replace `<COST_CENTER>` with the 3-digit cost center code (e.g., '859')

```sql
SELECT
    account_rollup,
    SUM(amount_usd) as spend
FROM EXPENSEMASTER_DB.RHAI_MARTS.GL_SUB_LEDGER_AGGREGATE
WHERE cost_center_code = '<COST_CENTER>'
  AND YEAR(period_date) = YEAR(CURRENT_DATE())
  AND MONTH(period_date) = 6
GROUP BY account_rollup
ORDER BY spend DESC;
```

### 7.7 How do I look up transactions by purchase order number?

**Parameters**: Replace `<PO_NUMBER>` with the purchase order number (e.g., '1010104566')

```sql
SELECT
    period_date,
    period_name,
    vendor_customer,
    amount_usd,
    je_category_name
FROM EXPENSEMASTER_DB.RHAI_MARTS.GL_SUB_LEDGER_AGGREGATE
WHERE po_number = '<PO_NUMBER>'
ORDER BY period_date ASC;
```
