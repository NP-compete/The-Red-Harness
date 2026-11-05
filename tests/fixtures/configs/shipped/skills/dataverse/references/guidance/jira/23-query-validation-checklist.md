<!-- jira · from 02-4-advanced-patterns.md -->
### 🔍 Query Validation Checklist
```sql
-- Run this to validate your query results
WITH validation AS (
    -- Your query here
)
SELECT
    COUNT(*) as total_rows,
    COUNT(DISTINCT project_key) as unique_projects,
    MIN(created_date) as earliest_date,
    MAX(created_date) as latest_date,
    CASE
        WHEN COUNT(*) = 0 THEN 'ERROR: No results'
        WHEN COUNT(*) > 10000 THEN 'WARNING: Large result set'
        ELSE 'OK'
    END as status
FROM validation;
```

### ⚡ Performance Tips

See **[Section 7: Query Performance Optimization](#7-query-performance-optimization-guide)** for critical performance guidance on large tables.

---
