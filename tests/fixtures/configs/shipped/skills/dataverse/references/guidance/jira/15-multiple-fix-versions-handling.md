<!-- jira · from 02-4-advanced-patterns.md -->
### 🔀 Multiple Fix Versions Handling
```sql
-- Issues with BOTH "Committed" AND "PI-CY25Q4"
WITH committed_issues AS (
    SELECT DISTINCT ji.id
    FROM jira_db.cloudrhai_marts.jira_issue_non_pii ji
    JOIN jira_db.cloudrhai_marts.jira_nodeassociation_rhai na
        ON ji.id = na.source_node_id AND na.association_type = 'IssueFixVersion'
    JOIN jira_db.cloudrhai_marts.jira_projectversion_non_pii v
        ON na.sink_node_id = v.id
    WHERE UPPER(v.vname) LIKE '%COMMITTED%'
),
quarter_issues AS (
    SELECT DISTINCT ji.id
    FROM jira_db.cloudrhai_marts.jira_issue_non_pii ji
    JOIN jira_db.cloudrhai_marts.jira_nodeassociation_rhai na
        ON ji.id = na.source_node_id AND na.association_type = 'IssueFixVersion'
    JOIN jira_db.cloudrhai_marts.jira_projectversion_non_pii v
        ON na.sink_node_id = v.id
    WHERE v.vname LIKE '%PI-CY25Q4%'
)
SELECT ji.* FROM jira_db.cloudrhai_marts.jira_issue_non_pii ji
WHERE ji.id IN (SELECT id FROM committed_issues)
  AND ji.id IN (SELECT id FROM quarter_issues);
```
