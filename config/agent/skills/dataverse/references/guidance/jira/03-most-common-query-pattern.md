<!-- jira · from 01-table-of-contents.md -->
### 🚀 Most Common Query Pattern
```sql
-- Universal pattern for 80% of queries
WITH project_scope AS (
    SELECT pkey, pname FROM jira_db.cloudrhai_marts.jira_project_rhai
    WHERE UPPER(pname) LIKE '%{PROJECT_TERM}%' OR pkey = '{PROJECT_KEY}'
    LIMIT 1
)
SELECT
    ji.issue_key,
    it.pname as issue_type,
    ji.summary,
    js.pname as status,
    CASE js.statuscategory
        WHEN 2 THEN 'To Do'
        WHEN 4 THEN 'In Progress'
        WHEN 3 THEN 'Done'
    END as status_category
FROM jira_db.cloudrhai_marts.jira_issue_non_pii ji
JOIN project_scope ps ON ji.project = ps.pkey
JOIN jira_db.cloudrhai_marts.jira_issuetype_rhai it ON ji.issuetype = it.id
JOIN jira_db.cloudrhai_marts.jira_issuestatus_rhai js ON ji.issuestatus = js.id
WHERE js.statuscategory IN (2, 4)  -- Open items
ORDER BY ji.issue_key;
```

---

## 2. Core Query Patterns
