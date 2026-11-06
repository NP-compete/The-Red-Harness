<!-- jira · from 01-table-of-contents.md -->
### Pattern #1: Project Discovery (Use for any project mention)
```sql
WITH project_search AS (
    SELECT pkey, pname
    FROM jira_db.cloudrhai_marts.jira_project_rhai
    WHERE pkey = UPPER('{SEARCH_TERM}')  -- Exact match first
       OR UPPER(pname) LIKE '%{SEARCH_TERM}%'  -- Fuzzy match
    ORDER BY CASE WHEN pkey = UPPER('{SEARCH_TERM}') THEN 1 ELSE 2 END
    LIMIT 1
)
-- Use in main query: JOIN project_search ps ON ji.project = ps.pkey
```
