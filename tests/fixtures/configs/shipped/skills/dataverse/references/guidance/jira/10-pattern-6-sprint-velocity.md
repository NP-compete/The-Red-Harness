<!-- jira · from 01-table-of-contents.md -->
### Pattern #6: Sprint Velocity
```sql
WITH sprint_data AS (
    SELECT
        sp.name as sprint_name,
        SUM(CASE WHEN js.statuscategory = 3 THEN cfv_sp.numbervalue ELSE 0 END) as velocity
    FROM jira_db.cloudrhai_marts.jira_issue_non_pii ji
    JOIN jira_db.cloud_marts.jira_customfieldvalue cfv_sprint
        ON ji.id = cfv_sprint.issue AND cfv_sprint.customfield_name = 'Sprint'
    JOIN jira_db.cloudrhai_marts.jira_sprint_rhai sp
        ON sp.id = CAST(cfv_sprint.stringvalue AS INTEGER)
    LEFT JOIN jira_db.cloud_marts.jira_customfieldvalue cfv_sp
        ON ji.id = cfv_sp.issue AND cfv_sp.customfield_name = 'Story Points'
    JOIN jira_db.cloudrhai_marts.jira_issuestatus_rhai js ON ji.issuestatus = js.id
    WHERE ji.project = '{PROJECT_KEY}' AND sp.closed = TRUE
    GROUP BY sp.name, sp.complete_date
    ORDER BY sp.complete_date DESC
)
SELECT * FROM sprint_data LIMIT 6;
```

### Pattern #7: Current Quarter Filtering (DEFAULT)
```sql
WITH current_quarter AS (
    SELECT
        'CY' || RIGHT(YEAR(CURRENT_DATE()), 2) || 'Q' || QUARTER(CURRENT_DATE()) as pattern,
        DATE_TRUNC('quarter', CURRENT_DATE()) as start_date
)
-- Apply as: WHERE v.vname LIKE '%' || cq.pattern || '%'
--        OR ji.created >= cq.start_date
```

### Pattern #8: Story Points
```sql
SELECT
    ji.issue_key,
    COALESCE(cfv.numbervalue, 0) as story_points
FROM jira_db.cloudrhai_marts.jira_issue_non_pii ji
LEFT JOIN jira_db.cloud_marts.jira_customfieldvalue cfv
    ON ji.id = cfv.issue AND cfv.customfield_id = 'customfield_10028';
```

### Pattern #9: Labels (IT-Priority, Interrupt, etc.)
```sql
SELECT ji.issue_key, lbl.label
FROM jira_db.cloudrhai_marts.jira_issue_non_pii ji
JOIN jira_db.cloudrhai_marts.jira_label_rhai lbl ON ji.id = lbl.issue
WHERE lbl.label IN ('IT-Priority', 'Interrupt', 'Committed');
```

### Pattern #10: Issue Dependencies
```sql
-- Find issues that are depended on
SELECT ji.issue_key, COUNT(*) as dependency_count
FROM jira_db.cloudrhai_marts.jira_issue_non_pii ji
JOIN jira_db.cloudrhai_marts.jira_issuelink_rhai il ON ji.id = il.source
WHERE il.linktype = 'depends on'
GROUP BY ji.issue_key;
```

---

## 3. Quick Reference Cards

### 📌 Critical Field IDs
```
Story Points:      'customfield_10028'  (customfield_id)
Sprint:            'customfield_10020'  (customfield_id)
Blocked:           'customfield_10517'  (customfield_id)
Size:              'customfield_10795'  (customfield_id)
Target Version:    'customfield_10855'  (customfield_id)
```

### 🔢 Issue Type IDs
```
Epic:              '10000'
Story:             '10009'
Task:              '10014'
Bug:               '10016'
Outcome:           '10130'
Initiative:        '10103'
Risk:              '10146'
Spike:             '10104'
Sub-task:          '10015'
```

### 🚦 Status Categories (Universal)
```
2 = To Do        (New, Backlog, Waiting)
4 = In Progress  (In Progress, Review)
3 = Done         (Closed, Resolved, Complete)
```

### 🗂️ Association Types
```
IssueFixVersion:   Links issue to version
IssueComponent:    Links issue to component
IssueToSprint:     Links issue to sprint (less common)
```
