<!-- expensemaster · from 07-business-definitions-logic-gl-onestream.md -->
### Runrate Calculation

**Definition**: `(Total spend in period / Days completed in period) * Total days in period`

**When to Use Runrate**:
- **Current (Incomplete) Month**: Due to accruals and journal entries, you will not have a "real time" view of actuals because there will always be amounts missing. Final actuals will be available at the end of the 2nd workday of the following month. Use runrate to project the full month.
- **Completed Month**: Use the full monthly total expense actuals directly. No runrate calculation needed. Will only be available for prior months.

**Constraint**: Always add "as of today" caveat to the response when using runrate projections.

```sql
-- Runrate = (Total spend in period / Days completed) * Total days in period
-- Only use for current (incomplete) month projections
SELECT
    period_date,
    SUM(amount_usd) as actual_spend,
    DAY(CURRENT_DATE()) as days_completed,
    DAY(LAST_DAY(CURRENT_DATE())) as total_days,
    (SUM(amount_usd) / DAY(CURRENT_DATE())) * DAY(LAST_DAY(CURRENT_DATE())) as projected_runrate
FROM EXPENSEMASTER_DB.RHAI_MARTS.GL_SUB_LEDGER_AGGREGATE
WHERE period_date = DATE_TRUNC('month', CURRENT_DATE())
GROUP BY period_date;
-- NOTE: Always caveat that current month is incomplete
```
