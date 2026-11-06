<!-- jira · the rules that apply to every query here -->
# Always apply — jira

Read this before writing any SQL for this product. Everything
below applies regardless of what the question asks.

### 🚨 CRITICAL: Understanding Table Sizes

The JIRA database contains **massive tables**. Understanding their scale is essential for writing efficient queries:

| Table | Row Count | Performance Impact |
|-------|-----------|-------------------|
| `jira_nodeassociation_rhai` | **5.7 million** | 🔴 Critical - joins are expensive |
| `jira_issue_non_pii` | **5.2 million** | 🔴 Critical - full scans are slow |
| `jira_issuelink_rhai` | **4.0 million** | 🔴 Critical - hierarchy queries |
| `jira_projectversion_non_pii` | 91,000 | 🟡 Medium |
| `jira_project_rhai` | 3,100 | 🟢 Small - safe to scan |
| `jira_issuestatus_rhai` | 377 | 🟢 Small - safe to scan |
| `jira_issuetype_rhai` | 83 | 🟢 Small - safe to scan |
| `jira_issuelinktype_rhai` | 15 | 🟢 Small - safe to scan |

**Node Association Breakdown** (5.7M total):
- `IssueComponent`: 2.9 million rows
- `IssueFixVersion`: 1.8 million rows
- `IssueVersion`: 1.0 million rows
