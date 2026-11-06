<!-- jira · from 04-quick-command-reference.md -->
### Labels & Tags

| Business Term | Technical Implementation | Tables Required | Key Fields | Sample Values |
|---------------|-------------------------|-----------------|------------|---------------|
| "Issues with label X" | Label associations | JIRA_LABEL_RHAI + JIRA_ISSUE_NON_PII | JOIN on issue, filter label | "SalesPlanningCY26", "AI-Initiative" |
| "Labels starting with Y" | Pattern matching on labels | JIRA_LABEL_RHAI | WHERE label LIKE 'Y%' | "AI%", "Customer%" |

---

## Complete Field Dictionary
