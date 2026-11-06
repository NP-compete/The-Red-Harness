<!-- jira · from 03-7-query-performance-optimization-guide.md -->
### 🔗 Relationship Patterns Summary

**Hierarchy (Parent-Child):**
```sql
JOIN jira_db.cloudrhai_marts.jira_issuelink_rhai il ON parent.id = il.source
JOIN jira_db.cloudrhai_marts.jira_issue_non_pii child ON il.destination = child.id
```

**Versions:**
```sql
JOIN jira_nodeassociation_rhai na ON ji.id = na.source_node_id
    AND na.association_type = 'IssueFixVersion'
JOIN jira_projectversion_non_pii v ON na.sink_node_id = v.id
```

**Sprints:**
```sql
JOIN jira_customfieldvalue cfv ON ji.id = cfv.issue
    AND cfv.customfield_name = 'Sprint'
JOIN jira_sprint_rhai sp ON sp.id = CAST(cfv.stringvalue AS INTEGER)
```

**Story Points:**
```sql
LEFT JOIN jira_db.cloud_marts.jira_customfieldvalue cfv ON ji.id = cfv.issue
    AND cfv.customfield_name = 'Story Points'
-- Use: COALESCE(cfv.numbervalue, 0) as story_points
```

### 📅 Date Handling Reference

| Field | Table | Conversion Required | Example |
|-------|-------|-------------------|---------|
| created, updated | jira_issue_non_pii | No | `ji.created::DATE` |
| start_date, end_date | jira_sprint_rhai | Yes (milliseconds) | `TO_TIMESTAMP(start_date/1000)::DATE` |
| resolutiondate | jira_issue_non_pii | No | `ji.resolutiondate::DATE` |

### 🔄 Sprint Naming Conventions
- Format: `CY[YY]Q[Q]SP[N] - [Team Name]`
- Example: `CY25Q4SP2 - Platform Int`
- **Important**: Sort by date, not sprint number (SP0 may come after SP5)

---
