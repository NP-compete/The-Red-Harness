<!-- jira · from 03-7-query-performance-optimization-guide.md -->
### 💡 Quick Reference: Safe vs Dangerous Operations

| Operation | Safety | Recommendation |
|-----------|--------|----------------|
| Filter by `issue_key` | 🟢 Safe | Always preferred |
| Filter by `project` (pkey) | 🟢 Safe | Use as primary filter |
| Join to `jira_project_rhai` | 🟢 Safe | 3K rows, no concern |
| Join to `jira_issuetype_rhai` | 🟢 Safe | 83 rows, no concern |
| Join to `jira_issuestatus_rhai` | 🟢 Safe | 377 rows, no concern |
| Join to `jira_issuelink_rhai` | 🟡 Caution | 4M rows - avoid OR in JOIN |
| Join to `jira_nodeassociation_rhai` | 🔴 Dangerous | 5.7M rows - always filter `association_type` |
| `LIKE '%term%'` on `summary` | 🟡 Caution | Scope to project first |
| `LIKE '%term%'` on `description` | 🔴 Dangerous | Avoid if possible |
| Full scan of `jira_issue_non_pii` | 🔴 Dangerous | 5.2M rows - always filter

---

## 8. Appendix
