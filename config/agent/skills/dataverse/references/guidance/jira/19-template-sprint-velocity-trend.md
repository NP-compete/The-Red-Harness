<!-- jira · from 02-4-advanced-patterns.md -->
### 🏃 Template: Sprint Velocity Trend
```sql
-- Parameters: {PROJECT_KEY}, {SPRINT_COUNT}
SELECT
    sp.name as sprint_name,
    sp.complete_date::DATE as completed_date,
    COUNT(DISTINCT ji.issue_key) as issues_completed,
    SUM(CASE WHEN js.statuscategory = 3 THEN cfv_sp.numbervalue ELSE 0 END) as velocity
FROM jira_db.cloudrhai_marts.jira_issue_non_pii ji
JOIN jira_db.cloud_marts.jira_customfieldvalue cfv_sprint
    ON ji.id = cfv_sprint.issue AND cfv_sprint.customfield_name = 'Sprint'
JOIN jira_db.cloudrhai_marts.jira_sprint_rhai sp
    ON sp.id = CAST(cfv_sprint.stringvalue AS INTEGER)
LEFT JOIN jira_db.cloud_marts.jira_customfieldvalue cfv_sp
    ON ji.id = cfv_sp.issue AND cfv_sp.customfield_name = 'Story Points'
JOIN jira_db.cloudrhai_marts.jira_issuestatus_rhai js ON ji.issuestatus = js.id
WHERE ji.project = '{PROJECT_KEY}'
  AND sp.closed = TRUE
GROUP BY sp.name, sp.complete_date
ORDER BY sp.complete_date DESC
LIMIT {SPRINT_COUNT};
```
