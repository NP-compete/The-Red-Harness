<!-- fammatrix · from 02-essential-query-patterns.md -->
### Pattern 12: Person-to-Cost-Center Lookup (for headcount/org queries mentioning a person)

When a user asks about a person's organization (e.g., "headcount for Marco Bill Peter's org"), the person may not map to a department code. Search the person's name across accountability columns: `BUDGET_OWNER`, `FINANCE_MANAGER`, `CC_OWNER`, and `FAM_GLOBAL`.

**⚠️ CRITICAL: Use tiered name matching** — match full name first, fall back to last name only if no full-name match. This prevents false positives (e.g., "Bill" matching "Bill Smith" when searching for "Marco Bill Peter").

```sql
-- "What cost centers does Marco Bill Peter own/manage?"
-- "Find the organization for Marco Bill Peter"
-- Tiered matching: full name first (Tier 0), last name fallback (Tier 1)
WITH person_cost_centers AS (
    SELECT
        COSTCENTER,
        DESCRIPTION,
        BUDGET_OWNER,
        FINANCE_MANAGER,
        CC_OWNER,
        FAM_GLOBAL,
        DEPT_1, DEPT_2, DEPT_3, DEPT_4, DEPT_5, DEPT_6,
        CASE
            WHEN BUDGET_OWNER ILIKE '%Marco%Bill%' THEN 0
            WHEN FINANCE_MANAGER ILIKE '%Marco%Bill%' THEN 0
            WHEN CC_OWNER ILIKE '%Marco%Bill%' THEN 0
            WHEN FAM_GLOBAL ILIKE '%Marco%Bill%' THEN 0
            WHEN BUDGET_OWNER ILIKE '%Bill%Peter%' THEN 0
            WHEN FINANCE_MANAGER ILIKE '%Bill%Peter%' THEN 0
            WHEN CC_OWNER ILIKE '%Bill%Peter%' THEN 0
            WHEN FAM_GLOBAL ILIKE '%Bill%Peter%' THEN 0
            ELSE 1
        END AS match_tier,
        CASE
            WHEN BUDGET_OWNER ILIKE '%Marco%Bill%' OR BUDGET_OWNER ILIKE '%Bill%Peter%' THEN 'BUDGET_OWNER: ' || BUDGET_OWNER
            WHEN FINANCE_MANAGER ILIKE '%Marco%Bill%' OR FINANCE_MANAGER ILIKE '%Bill%Peter%' THEN 'FINANCE_MANAGER: ' || FINANCE_MANAGER
            WHEN CC_OWNER ILIKE '%Marco%Bill%' OR CC_OWNER ILIKE '%Bill%Peter%' THEN 'CC_OWNER: ' || CC_OWNER
            WHEN FAM_GLOBAL ILIKE '%Marco%Bill%' OR FAM_GLOBAL ILIKE '%Bill%Peter%' THEN 'FAM_GLOBAL: ' || FAM_GLOBAL
            ELSE 'LAST_NAME_FALLBACK'
        END AS matched_on
    FROM fammatrix_db.marts.CONSOLIDATEDLIST
    WHERE BUDGET_OWNER ILIKE '%Marco%Bill%' OR BUDGET_OWNER ILIKE '%Bill%Peter%'
       OR FINANCE_MANAGER ILIKE '%Marco%Bill%' OR FINANCE_MANAGER ILIKE '%Bill%Peter%'
       OR CC_OWNER ILIKE '%Marco%Bill%' OR CC_OWNER ILIKE '%Bill%Peter%'
       OR FAM_GLOBAL ILIKE '%Marco%Bill%' OR FAM_GLOBAL ILIKE '%Bill%Peter%'
       OR BUDGET_OWNER ILIKE '%Peter%'
       OR FINANCE_MANAGER ILIKE '%Peter%'
       OR CC_OWNER ILIKE '%Peter%'
       OR FAM_GLOBAL ILIKE '%Peter%'
)
SELECT COSTCENTER, DESCRIPTION, matched_on,
       DEPT_1, DEPT_2, DEPT_3, DEPT_4, DEPT_5, DEPT_6
FROM person_cost_centers
WHERE match_tier = (SELECT MIN(match_tier) FROM person_cost_centers)
ORDER BY COSTCENTER;
```

> **When to use this pattern:** When the user asks about a specific person's organization, headcount, or cost centers — and the person name doesn't match a department code. Search `BUDGET_OWNER`, `FINANCE_MANAGER`, `CC_OWNER`, `FAM_GLOBAL` with tiered matching: full name first (Tier 0), last name fallback (Tier 1). Only show Tier 1 results if Tier 0 returns nothing.

> **Next step:** After finding the cost centers, strip the `CC` prefix and pass the codes to RoverPeople to count headcount:
> ```sql
> SELECT COUNT(DISTINCT uuid) as headcount
> FROM roverpeople_db.rhai_marts.rover_people_curr
> WHERE cost_center IN ('539','773','850', ...)
> ```
