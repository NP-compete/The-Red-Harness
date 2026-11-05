<!-- roverpeople · from 04-essential-query-templates-1.md -->
### Span of Control Analysis (Full Recursive Hierarchy with Guardrails)
```sql
-- Guardrails:
-- 1) Use ILIKE for case-insensitive search without LOWER() on columns.
-- 2) Cap recursion depth to prevent blowups (downward depth <= 8).
-- 3) Path-based cycle check and DISTINCT to avoid duplicates.
-- 4) Optional base size check: if more than 800 matches, tighten filters before running.
-- 5) IMPORTANT: Include last name fallback to handle nicknames (John→Jonathan, Bill→William).
WITH base_manager AS (
    SELECT uuid, name, mail
    FROM roverpeople_db.rhai_marts.rover_people_curr
    WHERE (
        name ILIKE '%Target Manager Name%'            -- Full name match — replace with actual name
        OR name ILIKE '%LastName%'                     -- Last name fallback — replace with actual last name
    )
    QUALIFY ROW_NUMBER() OVER (
        ORDER BY
            CASE WHEN name ILIKE '%Target Manager Name%' THEN 0 ELSE 1 END,
            uuid
    ) = 1
),
base_count AS (
    SELECT COUNT(*) AS base_size FROM base_manager
),
reporting_hierarchy AS (
    -- Base case: start at the target manager
    SELECT
        b.uuid AS manager_uuid,
        b.name AS manager_name,
        b.mail AS manager_email,
        b.uuid AS employee_uuid,
        b.name AS employee_name,
        b.mail AS employee_email,
        p.job_role,
        p.cost_center_desc,
        p.geo,
        p.employee_type,
        0 AS level,
        CAST(b.uuid AS VARCHAR) AS path
    FROM base_manager b
    JOIN roverpeople_db.rhai_marts.rover_people_curr p ON p.uuid = b.uuid

    UNION ALL

    -- Recursive case: walk downward only
    SELECT
        h.manager_uuid,
        h.manager_name,
        h.manager_email,
        e.uuid AS employee_uuid,
        e.name AS employee_name,
        e.mail AS employee_email,
        e.job_role,
        e.cost_center_desc,
        e.geo,
        e.employee_type,
        h.level + 1 AS level,
        h.path || '>' || e.uuid AS path
    FROM reporting_hierarchy h
    JOIN roverpeople_db.rhai_marts.rover_people_curr e
        ON e.manager_uuid = h.employee_uuid
    WHERE e.uuid != e.manager_uuid                          -- Exclude self-reports
      AND h.level < 8                                       -- Depth cap
      AND h.path NOT LIKE '%' || e.uuid || '%'              -- Cycle check
)
SELECT
    manager_name,
    level,
    COUNT(DISTINCT employee_uuid) AS reports_at_level,      -- DISTINCT to avoid double count
    COUNT(DISTINCT CASE WHEN level = 1 THEN employee_uuid END) AS direct_reports,
    COUNT(DISTINCT CASE WHEN level > 1 THEN employee_uuid END) AS indirect_reports,
    (SELECT base_size FROM base_count) AS base_size_checked
FROM reporting_hierarchy
WHERE level > 0
GROUP BY manager_name, ROLLUP(level)
QUALIFY ROW_NUMBER() OVER (ORDER BY level NULLS FIRST) <= 5000  -- Row safety cap
ORDER BY level NULLS FIRST;
```

```sql
-- Concise Variant (Fast)
-- Questions (SAME query for all):
--   "Show me span of control for [Manager Name]"
--   "How many employees are in [Manager Name]'s org?"
--   "How many employees report to [Manager Name] directly and indirectly?"
-- Use RECURSIVE CTE to capture ALL direct and indirect reports
-- Guardrails: exact mail/kerberos lookup (no mail ILIKE 'user%'), depth cap (8), cycle check, DISTINCT counts.
WITH base_manager AS (
    SELECT uu
