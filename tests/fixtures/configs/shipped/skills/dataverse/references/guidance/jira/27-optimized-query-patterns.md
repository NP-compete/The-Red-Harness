<!-- jira · from 03-7-query-performance-optimization-guide.md -->
### ✅ Optimized Query Patterns

#### Pattern A: Efficient Issue Link Traversal
```sql
-- Split bidirectional link search into UNION (uses indexes on both columns)
WITH outgoing_links AS (
    SELECT
        il.destination as linked_issue_id,
        il.linktype as relationship
    FROM jira_db.cloudrhai_marts.jira_issuelink_rhai il
    WHERE il.source = {issue_id}
),
incoming_links AS (
    SELECT
        il.source as linked_issue_id,
        il.linktype as relationship
    FROM jira_db.cloudrhai_marts.jira_issuelink_rhai il
    WHERE il.destination = {issue_id}
)
SELECT * FROM outgoing_links
UNION
SELECT * FROM incoming_links;
```

#### Pattern B: Efficient Version Filtering
```sql
-- Always include association_type in JOIN condition
SELECT DISTINCT ji.issue_key, v.vname
FROM jira_db.cloudrhai_marts.jira_issue_non_pii ji
JOIN jira_db.cloudrhai_marts.jira_nodeassociation_rhai na
    ON ji.id = na.source_node_id
    AND na.association_type = 'IssueFixVersion'  -- Reduces 5.7M -> 1.8M
JOIN jira_db.cloudrhai_marts.jira_projectversion_non_pii v
    ON na.sink_node_id = v.id
WHERE ji.project = '{PROJECT_KEY}'  -- Filter by project first
  AND v.vname LIKE '%CY25Q4%';
```

#### Pattern C: Scoped Text Search
```sql
-- When text search is necessary, scope it to a specific project first
WITH project_issues AS (
    -- First, filter to a specific project (uses project index)
    SELECT ji.id, ji.issue_key, ji.summary, ji.issuetype
    FROM jira_db.cloudrhai_marts.jira_issue_non_pii ji
    WHERE ji.project = '{PROJECT_KEY}'
      AND ji.issuetype IN ('10158', '10003', '10000')  -- Strategic items only
)
-- Then apply text search on smaller result set
SELECT * FROM project_issues
WHERE UPPER(summary) LIKE '%{SEARCH_TERM}%';
```

#### Pattern D: Efficient Hierarchy Query
```sql
-- For parent-child relationships, use specific direction
WITH parent_issue AS (
    SELECT id FROM jira_db.cloudrhai_marts.jira_issue_non_pii
    WHERE issue_key = '{PARENT_KEY}'
),
-- Get children (parent is source, child is destination)
children AS (
    SELECT child.issue_key, child.summary, it.pname as issue_type
    FROM parent_issue p
    JOIN jira_db.cloudrhai_marts.jira_issuelink_rhai il ON p.id = il.source
    JOIN jira_db.cloudrhai_marts.jira_issue_non_pii child ON il.destination = child.id
    JOIN jira_db.cloudrhai_marts.jira_issuetype_rhai it ON child.issuetype = it.id
    WHERE child.issuetype = '10000'  -- Epics only
)
SELECT * FROM children;
```
