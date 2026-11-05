<!-- fammatrix · from 02-essential-query-patterns.md -->
### Pattern 11: Cross-Level Department Search (IT, PPL, etc.)

**⚠️ Snowflake LIKE/ILIKE note:** In Snowflake, `_` is a single-character wildcard in LIKE/ILIKE. Do NOT use `[_]` (SQL Server syntax) or bare `ILIKE '%IT_%'` (matches substrings). Use **REGEXP_LIKE** for accurate matching.

```sql
-- "What cost centers are in the IT organization?"
-- "Find all cost centers under IT"
-- CRITICAL: IT is NOT at DEPT_3. Search across ALL department levels using REGEXP_LIKE.
SELECT
    COSTCENTER,
    DESCRIPTION,
    DEPT_1, DEPT_2, DEPT_3, DEPT_4, DEPT_5, DEPT_6
FROM fammatrix_db.marts.CONSOLIDATEDLIST
WHERE REGEXP_LIKE(DEPT_1, '^IT_.*') OR DEPT_1 = 'IT'
   OR REGEXP_LIKE(DEPT_2, '^IT_.*') OR DEPT_2 = 'IT'
   OR REGEXP_LIKE(DEPT_3, '^IT_.*') OR DEPT_3 = 'IT'
   OR REGEXP_LIKE(DEPT_4, '^IT_.*') OR DEPT_4 = 'IT'
   OR REGEXP_LIKE(DEPT_5, '^IT_.*') OR DEPT_5 = 'IT'
   OR REGEXP_LIKE(DEPT_6, '^IT_.*') OR DEPT_6 = 'IT'
ORDER BY DEPT_3, DEPT_4, DEPT_5, COSTCENTER;
```

> **Why REGEXP_LIKE?** `REGEXP_LIKE(DEPT_X, '^IT_.*')` matches values starting with `IT_` (like `IT_RH`, `IT_IBM`) but NOT `Digital` or `Benefits` which contain "IT" as a substring. The `OR DEPT_X = 'IT'` catches exact matches.

> **When to use this pattern:** Whenever the user asks about a department that is NOT one of the four DEPT_1 values (CORP, Total_SnS, PnGE, MKT). Always search all 6 levels. Replace `IT` with the search term (e.g., `PPL`, `FnA`, `BSO`).
