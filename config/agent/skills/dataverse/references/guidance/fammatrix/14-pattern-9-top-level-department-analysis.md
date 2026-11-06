<!-- fammatrix · from 02-essential-query-patterns.md -->
### Pattern 9: Top-Level Department Analysis
```sql
-- "How many cost centers are assigned to each top-level department?"
-- Include unique_finance_managers for management insight
SELECT
    DEPT_1,
    COUNT(DISTINCT COSTCENTER) as cost_center_count,
    COUNT(DISTINCT FINANCE_MANAGER) as unique_finance_managers
FROM fammatrix_db.marts.CONSOLIDATEDLIST
WHERE DEPT_1 IS NOT NULL
GROUP BY DEPT_1
ORDER BY cost_center_count DESC;
```
