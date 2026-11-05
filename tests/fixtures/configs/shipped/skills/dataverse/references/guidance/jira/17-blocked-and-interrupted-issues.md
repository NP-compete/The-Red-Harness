<!-- jira · from 02-4-advanced-patterns.md -->
### 🚫 Blocked and Interrupted Issues
```sql
-- Combined risk indicators
SELECT
    ji.issue_key,
    CASE WHEN cfo.customvalue = 'True' THEN 'Yes' ELSE 'No' END as blocked,
    CASE WHEN lbl.label IS NOT NULL THEN 'Yes' ELSE 'No' END as interrupted
FROM jira_db.cloudrhai_marts.jira_issue_non_pii ji
LEFT JOIN jira_db.cloud_marts.jira_customfieldvalue cfv_blocked
    ON ji.id = cfv_blocked.issue AND cfv_blocked.customfield_id = 'customfield_10517'
LEFT JOIN jira_db.cloudrhai_marts.jira_customfieldoption_rhai cfo
    ON cfv_blocked.stringvalue = cfo.id
LEFT JOIN jira_db.cloudrhai_marts.jira_label_rhai lbl
    ON ji.id = lbl.issue AND lbl.label IN ('Interrupt', 'interrupt')
WHERE ji.project = '{PROJECT_KEY}';
```

---

## 5. Template Library
