<!-- jira · from 01-table-of-contents.md -->
### Pattern #3: Version Filtering (Multiple versions per issue)
```sql
-- Issues with specific version
SELECT DISTINCT ji.issue_key, v.vname
FROM jira_db.cloudrhai_marts.jira_issue_non_pii ji
JOIN jira_db.cloudrhai_marts.jira_nodeassociation_rhai na
    ON ji.id = na.source_node_id
    AND na.association_type = 'IssueFixVersion'
JOIN jira_db.cloudrhai_marts.jira_projectversion_non_pii v
    ON na.sink_node_id = v.id
WHERE v.vname LIKE '%PI-CY25Q4%';
```
