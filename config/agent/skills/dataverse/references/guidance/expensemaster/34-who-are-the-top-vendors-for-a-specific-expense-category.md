<!-- expensemaster · from 08-golden-query-templates-gl-onestream-1.md -->
### 7.4 Who are the top vendors for a specific expense category?

**Parameters**: Replace `<EXPENSE_CATEGORY>` with expense type (e.g., 'Software', 'Travel', 'Consulting')

**Category Columns**:
- `account_name` - Detailed expense type (e.g., 'Computer Software Expense')
- `account_parent_cd` - Parent category for roll-ups (e.g., 'Equipement Expense')

```sql
-- Option 1: Filter by account_name (detailed)
SELECT
   vendor_customer,
   SUM(amount_usd) as total_usd,
   COUNT(DISTINCT po_number) as unique_pos
FROM EXPENSEMASTER_DB.RHAI_MARTS.GL_SUB_LEDGER_AGGREGATE
WHERE account_name ILIKE '%' || <EXPENSE_CATEGORY> || '%'  -- e.g., '%Software%'
  AND YEAR(period_date) = YEAR(CURRENT_DATE())
GROUP BY vendor_customer
ORDER BY total_usd DESC
LIMIT 10;

-- Option 2: Filter by account_parent_cd (roll-up category)
SELECT
   vendor_customer,
   SUM(amount_usd) as total_usd,
   COUNT(DISTINCT po_number) as unique_pos
FROM EXPENSEMASTER_DB.RHAI_MARTS.GL_SUB_LEDGER_AGGREGATE
WHERE account_parent_cd ILIKE '%' || <
