<!-- jira · from 04-quick-command-reference.md -->
### JIRA_ISSUE_NON_PII

| Field Name | Business Purpose | Sample Values | Common Filters |
|------------|------------------|---------------|----------------|
| issue_key | Unique identifier | "RHEA-1234", "SPT-5678" | `WHERE issue_key = 'RHEA-1234'` |
| issuetype | Issue type ID | "10000" (Epic), "10009" (Story) | `WHERE issuetype IN ('10000','10009')` |
| summary | Issue title/description | "App Forms UI/UX Refresh" | `WHERE summary ILIKE '%refresh%'` |
| priority | Priority level | "Major", "Critical", "Minor" | `WHERE priority = 'Critical'` |
| issuestatus | Current status ID | Join to jira_issuestatus_rhai | `WHERE issuestatus = js.id` |

### JIRA_ISSUELINK_RHAI

| Field Name | Business Purpose | Sample Values | Common Filters |
|------------|------------------|---------------|----------------|
| source | Parent issue ID | 12345, 67890 | JOIN condition for parent |
| destination | Child issue ID | 54321, 09876 | JOIN condition for child |
| linktype | Relationship type | 12310020, 12310620 | `WHERE linktype = 12310020` |

### JIRA_LABEL_RHAI

| Field Name | Business Purpose | Sample Values | Common Filters |
|------------|------------------|---------------|----------------|
| issue | Connected issue ID | 12345, 67890 | JOIN with JIRA_ISSUE_NON_PII.id |
| label | Actual label text | "AI-Initiative", "CustomerFacing" | `WHERE label LIKE 'AI%'` |

---

## Issue Type & Link Type Reference
