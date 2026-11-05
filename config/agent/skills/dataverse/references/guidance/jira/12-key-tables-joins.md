<!-- jira · from 01-table-of-contents.md -->
### 📊 Key Tables & Joins
```
jira_issue_non_pii ji        → Main issue table
├─ ji.project = jp.pkey      → jira_project_rhai jp
├─ ji.issuetype = it.id      → jira_issuetype_rhai it
├─ ji.issuestatus = js.id    → jira_issuestatus_rhai js
├─ ji.id = lbl.issue         → jira_label_rhai lbl
├─ ji.id = na.source_node_id → jira_nodeassociation_rhai na
└─ ji.id = il.source/dest    → jira_issuelink_rhai il
```

---
