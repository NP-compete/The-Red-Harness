<!-- jira · from 01-table-of-contents.md -->
### Pattern #4: IT-Priority Issues (SPECIAL RULES)
```sql
-- IT-Priority uses ALL projects, not just IT projects
SELECT ji.issue_key, ji.summary, jp.pname as project
FROM jira_db.cloudrhai_marts.jira_issue_non_pii ji
JOIN jira_db.cloudrhai_marts.jira_label_rhai lbl
    ON ji.id = lbl.issue AND lbl.label = 'IT-Priority'
JOIN jira_db.cloudrhai_marts.jira_project_rhai jp ON ji.project = jp.pkey
WHERE ji.issuetype = '10000';  -- Epic
```
