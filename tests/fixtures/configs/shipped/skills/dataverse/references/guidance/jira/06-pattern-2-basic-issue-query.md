<!-- jira · from 01-table-of-contents.md -->
### Pattern #2: Basic Issue Query
```sql
SELECT
    ji.issue_key,
    ji.summary,
    js.pname as status,
    it.pname as issue_type
FROM jira_db.cloudrhai_marts.jira_issue_non_pii ji
JOIN jira_db.cloudrhai_marts.jira_issuestatus_rhai js ON ji.issuestatus = js.id
JOIN jira_db.cloudrhai_marts.jira_issuetype_rhai it ON ji.issuetype = it.id
WHERE ji.project = '{PROJECT_KEY}'
  AND js.statuscategory IN (2, 4);  -- Open items
```
