<!-- fammatrix · from 02-essential-query-patterns.md -->
### Pattern 8: Complete Financial Chain (NO WHERE clause!)
```sql
-- "Show all cost centers with complete financial accountability chain"
-- CRITICAL: NO WHERE clause - show ALL records!
SELECT
    COSTCENTER, DESCRIPTION,
    FINANCE_MANAGER, FAM_GLOBAL,
    BUDGET_OWNER, CC_OWNER,
    CLT, HRBP,
    DEPT_1, DEPT_2
FROM fammatrix_db.marts.CONSOLIDATEDLIST
-- NO WHERE clause! Show ALL cost centers
ORDER BY DEPT_1, DEPT_2, COSTCENTER
LIMIT 50;  -- Always limit "show all" queries
```
