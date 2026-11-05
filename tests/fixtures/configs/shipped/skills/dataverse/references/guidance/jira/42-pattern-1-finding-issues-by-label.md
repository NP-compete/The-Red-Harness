<!-- jira · from 04-quick-command-reference.md -->
### Pattern 1: Finding Issues by Label

**Business Question:** "Find all epics with labels starting with 'AI'"

> �� **Performance:** Index on label recommended for LIKE queries

```sql
SELECT i.issue_key, i.summary, l.label
FROM jira_issue_non_pii i
JOIN jira_label_rhai l ON i.id = l.issue
WHERE i.issuetype = '10000' -- Epic
  AND l.label LIKE 'AI%'
ORDER BY i.issue_key;

-- Alternative for exact matches (faster):
WHERE l.label = 'AI-Initiative'
```

---
