<!-- jira · from 01-table-of-contents.md -->
### Pattern #5: IT Hierarchy (Outcome → Initiative → Epic)
```sql
-- Simplified 2-level hierarchy for IT queries
WITH parent_issues AS (
    SELECT ji.id FROM jira_db.cloudrhai_marts.jira_issue_non_pii ji
    WHERE ji.issue_key = '{PARENT_KEY}'
),
child_issues AS (
    SELECT child.*
    FROM parent_issues p
    JOIN jira_db.cloudrhai_marts.jira_issuelink_rhai il ON p.id = il.source
    JOIN jira_db.cloudrhai_marts.jira_issue_non_pii child ON il.destination = child.id
)
SELECT * FROM child_issues WHERE issuetype = '10000';  -- Epics
```
