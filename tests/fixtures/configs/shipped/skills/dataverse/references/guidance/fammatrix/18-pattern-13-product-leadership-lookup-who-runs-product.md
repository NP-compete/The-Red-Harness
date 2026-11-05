<!-- fammatrix · from 02-essential-query-patterns.md -->
### Pattern 13: Product Leadership Lookup ("Who runs [product]?")

Use the Product Name → Department Mapping tables above to resolve the product name to DEPT values, then query for both BU and Engineering leadership.

```sql
SELECT
    COSTCENTER,
    DESCRIPTION,
    BUDGET_OWNER,
    CC_OWNER,
    DEPT_2, DEPT_3, DEPT_5,
    CASE
        WHEN DEPT_2 = 'Products' THEN 'BU / Product Management'
        WHEN DEPT_2 = 'Global_Engineering' THEN 'Engineering / R&D'
        ELSE DEPT_2
    END AS leadership_side
FROM fammatrix_db.marts.CONSOLIDATEDLIST
WHERE DEPT_3 = 'Hybrid_Platforms_BU'
   OR DEPT_5 = 'RnD_Hybrid_Platforms'
ORDER BY leadership_side, COSTCENTER;
-- @AGENT_NOTE: Strip CC prefix from COSTCENTERs, query roverpeople for VPs/Sr Directors in those cost centers.
-- @AGENT_NOTE: Use BUDGET_OWNER from fammatrix for BU leadership, RoverPeople titles for Engineering leadership.
-- @AGENT_NOTE: Present both BU (Product Management) and Engineering (R&D) sides in the final answer.
```

> **When to use this pattern:** When the user asks "Who runs [product]?", "Who leads [product]?", or "Who is in charge of [product]?". Always use the Product Name → Department Mapping tables to resolve the product name first — do NOT search DEPT columns directly for product names like "OpenShift".

---
