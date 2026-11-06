<!-- jira · from 03-7-query-performance-optimization-guide.md -->
### 🚫 Anti-Patterns to AVOID

#### ❌ Anti-Pattern #1: LIKE '%pattern%' on Large Text Fields
```sql
-- ❌ TERRIBLE: Full table scan of 5.2M rows with large text field
WHERE UPPER(ji.description) LIKE '%SEARCH_TERM%'

-- ❌ BAD: Still scans entire table, but smaller field
WHERE UPPER(ji.summary) LIKE '%SEARCH_TERM%'

-- ✅ BETTER: Use specific project key first, then search within
WHERE ji.project = 'PROJECT_KEY'
  AND UPPER(ji.summary) LIKE '%SEARCH_TERM%'

-- ✅ BEST: Use exact match on indexed columns
WHERE ji.issue_key = 'PROJECT-123'
```

**Why it's slow**: Leading `%` prevents index usage, forcing full table scan of millions of rows.

#### ❌ Anti-Pattern #2: OR Conditions in JOIN Clauses
```sql
-- ❌ TERRIBLE: OR in JOIN prevents index usage on 4M row table
JOIN jira_issuelink_rhai il
    ON (parent.id = il.source OR parent.id = il.destination)

-- ✅ BETTER: Split into UNION for index usage
WITH links_as_source AS (
    SELECT il.destination as linked_id, il.linktype
    FROM jira_issuelink_rhai il
    WHERE il.source = {parent_id}
),
links_as_destination AS (
    SELECT il.source as linked_id, il.linktype
    FROM jira_issuelink_rhai il
    WHERE il.destination = {parent_id}
)
SELECT * FROM links_as_source
UNION
SELECT * FROM links_as_destination
```

#### ❌ Anti-Pattern #3: Overly Broad Project Filters
```sql
-- ❌ TERRIBLE: Matches 430+ projects (14% of all projects!)
WHERE UPPER(jp.pname) LIKE '%DATA%'
   OR UPPER(jp.pname) LIKE '%PLATFORM%'
   OR UPPER(jp.pname) LIKE '%AI%'

-- ✅ BETTER: Use explicit project keys
WHERE jp.pkey IN ('RHEA', 'DEAI', 'IDP', 'DATAPROD', 'ITEAI')
```

**Why it's slow**: Broad LIKE patterns can match hundreds of projects, inflating result sets to 800K+ issues.

#### ❌ Anti-Pattern #4: Late Filtering on Node Associations
```sql
-- ❌ BAD: Joins 5.7M rows then filters
JOIN jira_nodeassociation_rhai na ON ji.id = na.source_node_id
WHERE na.association_type = 'IssueFixVersion'

-- ✅ BETTER: Filter in JOIN condition (filtered before join processing)
JOIN jira_nodeassociation_rhai na
    ON ji.id = na.source_node_id
    AND na.association_type = 'IssueFixVersion'  -- Filter 5.7M → 1.8M immediately
```

#### ❌ Anti-Pattern #5: Double Joins on Large Tables
```sql
-- ❌ TERRIBLE: Joins nodeassociation (5.7M) twice without early filtering
JOIN jira_nodeassociation_rhai na1 ON e.id = na1.source_node_id
JOIN jira_projectversion_non_pii v ON na1.sink_node_id = v.id
JOIN jira_nodeassociation_rhai na2 ON v.id = na2.sink_node_id  -- Second join!

-- ✅ BETTER: Filter association_type in each join
JOIN jira_nodeassociation_rhai na1
    ON e.id = na1.source_node_id
    AND na1.association_type = 'IssueFixVersion'
JOIN jira_projectversion_non_pii v ON na1.sink_node_id = v.id
JOIN jira_nodeassociation_rhai na2
    ON v.id = na2.sink_node_id
    AND na2.association_type = 'IssueFixVersion'
```
