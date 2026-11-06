<!-- jira · from 04-quick-command-reference.md -->
### Pattern 2: Epic Children Count

**Business Question:** "Find epics with more than 3 children"

> �� **Performance:** Large datasets may require partitioning by project

```sql
SELECT
    parent.issue_key,
    parent.summary,
    COUNT(DISTINCT child.id) as child_count,
    LISTAGG(DISTINCT child.issue_key, ', ') as child_keys
FROM jira_db.cloudrhai_marts.jira_issue_non_pii parent
JOIN jira_db.cloudrhai_marts.jira_issuelink_rhai il ON parent.id = il.source
JOIN jira_db.cloudrhai_marts.jira_issue_non_pii child ON il.destination = child.id
JOIN jira_db.cloudrhai_marts.jira_issuestatus_rhai js ON parent.issuestatus = js.id
WHERE parent.issuetype = '10000'
  AND js.pname NOT IN ('Closed', 'Done', 'Resolved')
GROUP BY parent.issue_key, parent.summary
HAVING COUNT(DISTINCT child.id) > 3
ORDER BY child_count DESC;
```

---
