<!-- expensemaster · from 08-golden-query-templates-gl-onestream-1.md -->
## 📊 Golden Query Templates (GL & OneStream)

Ready-made SQL patterns for variance, headcount, vendors, spend breakdown, PO lookup, and quarter total. Apply [Critical rules](#-critical-rules) (GL & OneStream subsection), [amount column](#amount-columns-when-to-use-which), and [hierarchy/alias](#️-important-common-aliases-apply-to-all-queries) rules to these templates.

### 7.1 What is the monthly spend trend for cost center 999 over the last 12 months?
```sql
SELECT
   period_name,
   SUM(amount_usd) as total_spend
FROM EXPENSEMASTER_DB.RHAI_MARTS.GL_SUB_LEDGER_AGGREGATE
WHERE cost_center_code = '999'
  AND period_date >= DATEADD('month', -12, CURRENT_DATE())
GROUP BY period_name
ORDER BY MIN(period_date) DESC;
```
