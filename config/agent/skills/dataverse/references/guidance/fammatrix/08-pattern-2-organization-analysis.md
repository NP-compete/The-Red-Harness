<!-- fammatrix · from 02-essential-query-patterns.md -->
### Pattern 2: Organization Analysis
```sql
-- "Get me a cost center analysis across Red Hat's organizations"
-- SIMPLE: Just DEPT_1, count, and LISTAGG
SELECT
    DEPT_1,
    COUNT(DISTINCT COSTCENTER) as cost_center_count,
    LISTAGG(DISTINCT COSTCENTER, ', ') WITHIN GROUP (ORDER BY COSTCENTER) as cost_centers
FROM fammatrix_db.marts.CONSOLIDATEDLIST
GROUP BY DEPT_1
ORDER BY cost_center_count DESC;
```
