<!-- jira · from 04-quick-command-reference.md -->
### Pattern 4: Cross-Product Analysis

**Business Question:** "Find customer-facing epics with high priority"

> **Requires:** Customer data product first, then filter Jira
> - **Step 1:** Get customer-facing projects from Customer data product
> - **Step 2:** Filter Jira epics for those projects

```sql
SELECT
      i.issue_key,
      i.summary,
      CASE i.priority
        WHEN 10001 THEN 'Critical'
        WHEN 10002 THEN 'Major'
        ELSE 'Other'
      END as priority,
      LISTAGG(DISTINCT l.label, ', ') as labels
  FROM jira_db.cloudrhai_marts.jira_issue_non_pii i
  LEFT JOIN jira_db.cloudrhai_marts.jira_label_rhai l ON i.id = l.issue
  WHERE i.issuetype = '10000'
    AND i.priority IN (10001, 10002)
    AND i.project IN ('RHEA', 'SPT', 'RHMAP')
  GROUP BY i.issue_key, i.summary, i.priority
  ORDER BY
    CASE i.priority
      WHEN 10001 THEN 1
      WHEN 10002 THEN 2
      ELSE 3
    END;
```
---

**🎯 Remember**: Start simple, add complexity only when needed. Use the Quick Start patterns for 80% of queries.
