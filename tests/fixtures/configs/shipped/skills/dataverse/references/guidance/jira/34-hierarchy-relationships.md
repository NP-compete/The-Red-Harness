<!-- jira · from 04-quick-command-reference.md -->
### Hierarchy Relationships

| Business Term | Technical Implementation | Tables Required | Key Fields | Sample Values |
|---------------|-------------------------|-----------------|------------|---------------|
| "Children of Initiative" | Epics linked to Initiative | JIRA_ISSUELINK_RHAI + JIRA_ISSUE_NON_PII | linktype = 12310620, parent.issuetype = 10100 | RHEA-1234, SPT-5678 |
| "Stories under Epic" | Stories linked via Epic-Story Link | JIRA_ISSUELINK_RHAI + JIRA_ISSUE_NON_PII | linktype = 12310020, parent.issuetype = 16 | RHMAP-4427, FH-4630 |
| "Tasks in Epic" | Tasks linked to Epic | JIRA_ISSUELINK_RHAI + JIRA_ISSUE_NON_PII | linktype = 12310620, parent.issuetype = 16 | Task-123, BUILD-456 |
| "Parent of Story" | Epic containing the Story | JIRA_ISSUELINK_RHAI + JIRA_ISSUE_NON_PII | linktype = 12310020, child.issuetype = 17 | RHMAP-4363 |
