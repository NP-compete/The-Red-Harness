<!-- fammatrix · from 02-essential-query-patterns.md -->
### Pattern 10: External Reporting (IGNORE "by department" phrase!)
```sql
-- "What is the external reporting category breakdown?"
-- "What is the external reporting category breakdown by department?"
-- CRITICAL: Both questions want the SAME thing - just external reporting totals!
-- IGNORE "by department" - it's misleading! Do NOT add DEPT_1!
-- ONLY these 2 columns - nothing more!
SELECT
    EXTERNAL_REPORTING,
    COUNT(DISTINCT COSTCENTER) as cost_center_count  -- ONLY these 2 columns!
FROM fammatrix_db.marts.CONSOLIDATEDLIST
WHERE EXTERNAL_REPORTING IS NOT NULL
GROUP BY EXTERNAL_REPORTING  -- NEVER add DEPT_1 here even if question says "by department"!
ORDER BY cost_center_count DESC;
```
