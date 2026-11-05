<!-- jira · from 04-quick-command-reference.md -->
## Quick Command Reference

```sql
-- Find project by name
SELECT pkey, pname FROM jira_db.cloudrhai_marts.jira_project_rhai
WHERE UPPER(pname) LIKE '%SEARCH%';

-- Get issue type IDs
SELECT id, pname FROM jira_db.cloudrhai_marts.jira_issuetype_rhai
ORDER BY pname;

-- Get status IDs and categories
SELECT id, pname, statuscategory FROM jira_db.cloudrhai_marts.jira_issuestatus_rhai
ORDER BY statuscategory, pname;

-- Check if issue exists
SELECT issue_key, summary FROM jira_db.cloudrhai_marts.jira_issue_non_pii
WHERE issue_key = 'PROJECT-123';

-- Get custom field IDs
SELECT id, cfname FROM jira_db.cloud_marts.jira_customfield
WHERE cfname LIKE '%Story%';
```

## Issue Hierarchy Structure

```
Outcome (Level 1)
└── Initiative (Level 2)
    └── Epic (Level 3)
        └── Story (Level 4)
        └── Task (Level 4)
            └── Sub-task (Level 5)
```

---

## Business Terminology → Database Field Mapping
