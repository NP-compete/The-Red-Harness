<!-- jira · from 03-7-query-performance-optimization-guide.md -->
### 🎯 Query Optimization Checklist

Before executing any query against JIRA tables, verify:

- [ ] **No `LIKE '%pattern%'` on description field** (5.2M large text scans)
- [ ] **No `LIKE '%pattern%'` on summary without project scope**
- [ ] **No `OR` conditions in JOIN clauses** - use `UNION` instead
- [ ] **`association_type` filter in JOIN condition** for nodeassociation table
- [ ] **Explicit project keys** instead of broad `LIKE '%AI%'` patterns
- [ ] **Project or issue_key filter applied early** in the query
- [ ] **LIMIT clause** for exploratory queries
