<!-- fammatrix · from 02-essential-query-patterns.md -->
### Pattern 3: Department Hierarchy (Different columns for different queries)
```sql
-- "Show hierarchy for Corporate Functions" - Use ONLY DEPT_1, DEPT_2, DEPT_3
-- CRITICAL: Corporate Functions needs BOTH patterns but ONLY 3 dept levels!
SELECT
    DEPT_1, DEPT_2, DEPT_3,  -- Corporate: Only first 3 levels
    COUNT(DISTINCT COSTCENTER) as cost_center_count
FROM fammatrix_db.marts.CONSOLIDATEDLIST
WHERE
    DEPT_1 LIKE '%Corporate%' OR DEPT_1 = 'CORP'  -- BOTH patterns required
GROUP BY DEPT_1, DEPT_2, DEPT_3
ORDER BY DEPT_2, DEPT_3;

-- "List departments under Marketing" - Include ALL 6 DEPT columns
SELECT DISTINCT
    DEPT_1, DEPT_2, DEPT_3, DEPT_4, DEPT_5, DEPT_6,  -- Marketing: All 6 levels
    COUNT(COSTCENTER) as cost_center_count
FROM fammatrix_db.marts.CONSOLIDATEDLIST
WHERE
    DEPT_1 LIKE '%Marketing%' OR DEPT_1 = 'MKT'
GROUP BY DEPT_1, DEPT_2, DEPT_3, DEPT_4, DEPT_5, DEPT_6
ORDER BY DEPT_2, DEPT_3, DEPT_4;
```
