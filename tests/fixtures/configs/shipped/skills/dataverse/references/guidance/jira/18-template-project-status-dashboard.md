<!-- jira · from 02-4-advanced-patterns.md -->
### 📊 Template: Project Status Dashboard
```sql
-- Parameters: {PROJECT_KEY}, {QUARTER_PATTERN}
WITH project_metrics AS (
    SELECT
        ji.project,
        it.pname as issue_type,
        js.statuscategory,
        COUNT(*) as issue_count,
        SUM(COALESCE(cfv_sp.numbervalue, 0)) as total_points
    FROM jira_db.cloudrhai_marts.jira_issue_non_pii ji
    JOIN jira_db.cloudrhai_marts.jira_issuetype_rhai it ON ji.issuetype = it.id
    JOIN jira_db.cloudrhai_marts.jira_issuestatus_rhai js ON ji.issuestatus = js.id
    LEFT JOIN jira_db.cloud_marts.jira_customfieldvalue cfv_sp
        ON ji.id = cfv_sp.issue AND cfv_sp.customfield_id = 'customfield_10028'
    WHERE ji.project = '{PROJECT_KEY}'
    GROUP BY ji.project, it.pname, js.statuscategory
)
SELECT
    issue_type,
    SUM(CASE WHEN statuscategory = 2 THEN issue_count ELSE 0 END) as todo_count,
    SUM(CASE WHEN statuscategory = 4 THEN issue_count ELSE 0 END) as in_progress_count,
    SUM(CASE WHEN statuscategory = 3 THEN issue_count ELSE 0 END) as done_count,
    SUM(total_points) as total_story_points
FROM project_metrics
GROUP BY issue_type
ORDER BY total_story_points DESC;
```
