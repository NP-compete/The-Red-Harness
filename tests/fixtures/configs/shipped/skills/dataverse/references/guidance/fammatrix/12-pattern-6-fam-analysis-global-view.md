<!-- fammatrix · from 02-essential-query-patterns.md -->
### Pattern 6: FAM Analysis (Global View)
```sql
-- "Which FAM leads support the EMEA region?"
-- NOTE: This typically means ALL FAMs, not filtering by region!
SELECT DISTINCT
    FAM_GLOBAL,
    COUNT(DISTINCT COSTCENTER) as cost_center_count
FROM fammatrix_db.marts.CONSOLIDATEDLIST
WHERE FAM_GLOBAL IS NOT NULL
    AND FAM_GLOBAL NOT LIKE '#N/A%'
GROUP BY FAM_GLOBAL
ORDER BY cost_center_count DESC;
```

### Pattern 7: CLT Assignments (Check ALL columns)
```sql
-- "What cost centers have a CLT assignment?"
-- Check ALL CLT columns with OR
SELECT
    COSTCENTER, DESCRIPTION,
    CLT, CLT_1, CLT_2,
    FINANCE_MANAGER, DEPT_1, DEPT_2
FROM fammatrix_db.marts.CONSOLIDATEDLIST
WHERE CLT IS NOT NULL
   OR CLT_1 IS NOT NULL
   OR CLT_2 IS NOT NULL  -- Check all three!
ORDER BY CLT, COSTCENTER;
```
