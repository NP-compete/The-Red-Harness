<!-- fammatrix · from 02-essential-query-patterns.md -->
### Pattern 5: Financial Manager Analysis
```sql
-- "List all finance managers and their cost center coverage"
-- EXACTLY 3 columns required - no extras!
SELECT
    FINANCE_MANAGER,
    COUNT(DISTINCT COSTCENTER) as cost_center_count,
    COUNT(DISTINCT DEPT_1) as departments_covered  -- ONLY these 3 columns
FROM fammatrix_db.marts.CONSOLIDATEDLIST
WHERE FINANCE_MANAGER IS NOT NULL
    AND FINANCE_MANAGER NOT LIKE '#N/A%'  -- Critical filter!
GROUP BY FINANCE_MANAGER
ORDER BY cost_center_count DESC
LIMIT 20;  -- Always limit manager lists
```
