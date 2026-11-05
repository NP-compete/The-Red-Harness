<!-- jira · from 02-4-advanced-patterns.md -->
### 📈 Template: Issue Resolution Time
```sql
-- Parameters: {PROJECT_KEY}, {ISSUE_TYPE_ID}
SELECT
    ji.issue_key,
    ji.created::DATE as created_date,
    ji.resolutiondate::DATE as resolved_date,
    DATEDIFF(day, ji.created, ji.resolutiondate) as resolution_days,
    js.pname as final_status
FROM jira_db.cloudrhai_marts.jira_issue_non_pii ji
JOIN jira_db.cloudrhai_marts.jira_issuestatus_rhai js ON ji.issuestatus = js.id
WHERE ji.project = '{PROJECT_KEY}'
  AND ji.issuetype = '{ISSUE_TYPE_ID}'
  AND ji.resolutiondate IS NOT NULL
  AND js.statuscategory = 3
ORDER BY resolution_days DESC;
```

---

## 6. Troubleshooting Guide
