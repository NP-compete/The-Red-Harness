<!-- fammatrix · from 02-essential-query-patterns.md -->
### Pattern 1: Specific Cost Center Lookup
```sql
-- "Who is the finance manager and finance lead for cc871?"
-- INCLUDE: COSTCENTER, DESCRIPTION, FINANCE_MANAGER, FAM_GLOBAL, BUDGET_OWNER, CC_OWNER, CLT
SELECT
    COSTCENTER,
    DESCRIPTION,
    FINANCE_MANAGER,
    FAM_GLOBAL as finance_lead,  -- Alias FAM_GLOBAL when asking for "finance lead"
    BUDGET_OWNER,
    CC_OWNER,
    CLT
FROM fammatrix_db.marts.CONSOLIDATEDLIST
WHERE COSTCENTER = 'CC871';
```
