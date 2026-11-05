<!-- jira · from 02-4-advanced-patterns.md -->
### 🔄 IT Hierarchy Complete Traversal
*Use only when explicitly needed for IT-Priority or hierarchy queries*

> ⚠️ **Performance Warning**: This recursive pattern uses OR in JOIN which is slow on 4M rows.
> For simple parent→child queries, use **Pattern #5** or the optimized patterns in **Section 7**.

```sql
-- Full bidirectional hierarchy traversal (Outcome ↔ Initiative ↔ Epic)
-- ⚠️ SLOW: Use only when bidirectional recursion is required
WITH RECURSIVE hierarchy AS (
    -- Base: Find target issue
    SELECT id, issue_key, issuetype, 0 as level
    FROM jira_db.cloudrhai_marts.jira_issue_non_pii
    WHERE issue_key = '{TARGET_KEY}'

    UNION ALL

    -- Recursive: Find all related via issue links (bidirectional)
    SELECT ji.id, ji.issue_key, ji.issuetype, h.level + 1
    FROM hierarchy h
    JOIN jira_db.cloudrhai_marts.jira_issuelink_rhai il
        ON h.id = il.source OR h.id = il.destination  -- ⚠️ OR is slow but needed here
    JOIN jira_db.cloudrhai_marts.jira_issue_non_pii ji
        ON (CASE WHEN h.id = il.source THEN il.destination ELSE il.source END) = ji.id
    WHERE h.level < 3  -- CRITICAL: Limit depth to prevent runaway queries
)
SELECT DISTINCT * FROM hierarchy WHERE issuetype = 10000;  --  Epics only
```

**Faster Alternative** (for unidirectional traversal):
```sql
-- Parent → Children only (much faster)
WITH parent AS (
    SELECT id FROM jira_db.cloudrhai_marts.jira_issue_non_pii WHERE issue_key = '{TARGET_KEY}'
)
SELECT child.issue_key, child.summary, child.issuetype
FROM parent p
JOIN jira_db.cloudrhai_marts.jira_issuelink_rhai il ON p.id = il.source
JOIN jira_db.cloudrhai_marts.jira_issue_non_pii child ON il.destination = child.id
WHERE child.issuetype = 10000;
```
