<!-- jira · from 03-7-query-performance-optimization-guide.md -->
### 📊 Performance Comparison Examples

| Query Type | Bad Pattern | Optimized Pattern | Improvement |
|------------|-------------|-------------------|-------------|
| Text search | `LIKE '%term%'` on 5.2M issues | Scope to project first | **10-50x faster** |
| Issue links | `OR` in JOIN condition | Split into `UNION` | **2-5x faster** |
| Node associations | Filter in `WHERE` clause | Filter in `JOIN` condition | **3x faster** |
| Project filter | `LIKE '%DATA%'` | Explicit `pkey IN (...)` | **10-100x faster** |
