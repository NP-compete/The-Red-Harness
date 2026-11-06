<!-- fammatrix · from 02-essential-query-patterns.md -->
### Pattern 4: Business Strategy & Operations (BSO)
```sql
-- "What are the cost centers supporting Business Strategy & operations?"
-- SIMPLE WHERE clause - just DEPT_3 = 'BSO', NO extra LIKE patterns!
SELECT
    COSTCENTER, DESCRIPTION,
    DEPT_1, DEPT_2, DEPT_3,
    FINANCE_MANAGER, BUDGET_OWNER
FROM fammatrix_db.marts.CONSOLIDATEDLIST
WHERE DEPT_3 = 'BSO'  -- Simple and direct!
ORDER BY COSTCENTER;
```
