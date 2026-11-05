<!-- jira · from 02-4-advanced-patterns.md -->
### 🎯 Template: IT-Priority Epic Progress
```sql
-- No parameters needed (searches all projects)
SELECT
    jp.pname as project_name,
    COUNT(DISTINCT ji.issue_key) as epic_count,
    COUNT(DISTINCT CASE WHEN js.statuscategory = 3 THEN ji.issue_key END) as completed,
    COUNT(DISTINCT CASE WHEN js.statuscategory = 4 THEN ji.issue_key END) as in_progress,
    COUNT(DISTINCT CASE WHEN js.statuscategory = 2 THEN ji.issue_key END) as todo
FROM jira_db.cloudrhai_marts.jira_issue_non_pii ji
JOIN jira_db.cloudrhai_marts.jira_label_rhai lbl
    ON ji.id = lbl.issue AND lbl.label = 'IT-Priority'
JOIN jira_db.cloudrhai_marts.jira_project_rhai jp ON ji.project = jp.pkey
JOIN jira_db.cloudrhai_marts.jira_issuestatus_rhai js ON ji.issuestatus = js.id
WHERE ji.issuetype = '10000'  -- Epic
GROUP BY jp.pname
ORDER BY epic_count DESC;
```
