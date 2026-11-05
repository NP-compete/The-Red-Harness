<!-- jira · from 04-quick-command-reference.md -->
### Pattern 3: Full Hierarchy Traversal

**Business Question:** "Show all work under Initiative X"

> �� **Performance:** Limit recursion depth to prevent runaway queries

```sql
WITH RECURSIVE hierarchy AS (
  -- Start with Initiative
  SELECT
    id, issue_key, summary, issuetype,
    0 as level,
    CAST(issue_key AS VARCHAR(1000)) as path
  FROM JIRA_ISSUE_NON_PII
  WHERE issue_key = 'INIT-123'

  UNION ALL

  -- Recursively find children (max 5 levels)
  SELECT
    child.id, child.issue_key, child.summary, child.issuetype,
    h.level + 1,
    h.path || ' -> ' || child.issue_key
  FROM hierarchy h
  JOIN JIRA_ISSUELINK_RHAI il ON h.id = il.source
  JOIN JIRA_ISSUE_NON_PII child ON il.destination = child.id
  WHERE il.linktype IN ('12310020', '12310620') -- Epic-Story or Parent-Child
    AND h.level < 5 -- Prevent infinite recursion
)
SELECT
  REPEAT('  ', level) || issue_key as indented_key,
  summary,
  level,
  path
FROM hierarchy
ORDER BY path;
```

---
