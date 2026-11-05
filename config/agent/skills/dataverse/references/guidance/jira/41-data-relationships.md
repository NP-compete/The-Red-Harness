<!-- jira · from 04-quick-command-reference.md -->
### Data Relationships

```
JIRA_ISSUE_NON_PII
       │
       ├── issue_key (Display)
       ├── issuetype (Classification)
       ├── summary (Description)
       │
       ▼
JIRA_ISSUELINK_RHAI (Relationships)
       │
       ├── source (Parent Issue)
       ├── destination (Child Issue)
       └── linktype (Relationship Type)

JIRA_LABEL_RHAI (Tags)
       │
       ├── issue → JIRA_ISSUE_NON_PII.id
       └── label (Tag Text)
```

---

## Common Query Patterns
