<!-- jira · from 03-7-query-performance-optimization-guide.md -->
### 📚 Complete Table Reference

| Table | Schema | Key Columns | Purpose |
|-------|--------|-------------|---------|
| `jira_issue_non_pii` | cloudrhai_marts | id, issue_key, project, issuetype, issuestatus | Main issue data |
| `jira_project_rhai` | cloudrhai_marts | id, pkey, pname | Project metadata |
| `jira_issuelink_rhai` | cloudrhai_marts | source, destination, linktype(string name) | Issue hierarchy |
| `jira_nodeassociation_rhai` | cloudrhai_marts | source_node_id, sink_node_id, association_type | Versions, components |
| `jira_sprint_rhai` | cloudrhai_marts | id, name, start_date, end_date, closed, started | Sprint metadata |
| `jira_customfieldvalue_non_pii` | cloudrhai_marts | issue, customfield_id, numbervalue, stringvalue | Custom fields |
| `jira_label_rhai` | cloudrhai_marts | issue, label | Issue labels |
| `jira_projectversion_non_pii` | cloudrhai_marts | id, vname, project | Fix versions |
| `jira_worklog_rhai` | cloudrhai_marts | id, issueid, timeworked | Time tracking |
| `jira_component_rhai` | cloudrhai_marts | id, project, cname | Components |
| `jira_changegroup_rhai` | cloudrhai_marts | id, issueid, created | Change groups |
| `jira_changeitem_non_pii` | cloudrhai_marts | id, groupid, field, oldvalue, newvalue | Change items |
| `jira_comment_non_pii` | cloudrhai_marts | id, issueid, body, created | Comments |
