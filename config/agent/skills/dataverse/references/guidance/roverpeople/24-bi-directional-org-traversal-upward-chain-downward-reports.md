<!-- roverpeople · from 07-essential-query-templates-4.md -->
### Bi-Directional Org Traversal (Upward Chain + Downward Reports Summary)
```sql
-- Question: "Show reporting chain to CEO AND all direct/indirect reports for bkearney@redhat.com"
-- ⚠️ CRITICAL: NEVER put both upward and downward traversal in a single recursive CTE.
-- Uses TWO separate recursive CTEs: upward_chain (detailed) + downward_reports (summarised).
-- Guardrails:
-- 1) QUALIFY ROW_NUMBER() = 1 on target to anchor to exactly one person.
-- 2) base_count CTE to verify single anchor (exposed as base_size_checked in output).
-- 3) m.uuid != uc.uuid in upward to stop self-reporting executives (CEO).
-- 4) e.uuid != e.manager_uuid in downward to stop self-reporting loops.
-- 5) Path-based cycle check on both CTEs.
-- 6) Depth caps: upward ≤ 15, downward ≤ 10.
-- 7) QUALIFY row cap (≤ 5000) on final output.
-- 8) Downward returns summary counts per level, not individual rows.
-- Depth convention: negative = above target, 0 = target, positive = below target.
WITH RECURSIVE
target_employee AS (
    SELECT uuid, name, mail, title, job_role, employee_type,
           cost_center, cost_center_desc, geo, hire_date, manager_uuid
    FROM roverpeople_db.rhai_marts.rover_people_curr
    WHERE mail ILIKE 'bkearney@redhat.com'            -- Exact kerberos — replace
    QUALIFY ROW_NUMBER() OVER (ORDER BY uuid) = 1     -- Single anchor
),
base_count AS (
    SELECT COUNT(*) AS base_size FROM target_employee
),
upward_chain AS (
    SELECT p.uuid, p.name, p.mail, p.title, p.job_role, p.employee_type,
           p.cost_center, p.cost_center_desc, p.geo, p.hire_date, p.manager_uuid,
           0 AS depth, CAST(p.uuid AS VARCHAR) AS path
    FROM target_employee p
    UNION ALL
    SELECT m.uuid, m.name, m.mail, m.title, m.job_role, m.employee_type,
           m.cost_center, m.cost_center_desc, m.geo, m.hire_date, m.manager_uuid,
           uc.depth - 1, uc.path || '->' || m.uuid
    FROM roverpeople_db.rhai_marts.rover_people_curr m
    JOIN upward_chain uc ON m.uuid = uc.manager_uuid
    WHERE m.uuid != uc.uuid                           -- Stop self-reporting (CEO)
      AND uc.path NOT LIKE '%' || m.uuid || '%'       -- Cycle check
      AND uc.depth > -15                               -- Depth cap
),
downward_reports AS (
    SELECT p.uuid, p.employee_type, p.geo, p.cost_center_desc,
           0 AS depth, CAST(p.uuid AS VARCHAR) AS path
    FROM target_employee p
    UNION ALL
    SELECT e.uuid, e.employee_type, e.geo, e.cost_center_desc,
           dr.depth + 1, dr.path || '->' || e.uuid
    FROM roverpeople_db.rhai_marts.rover_people_curr e
    JOIN downward_reports dr ON e.manager_uuid = dr.uuid
    WHERE e.uuid != e.manager_uuid                     -- Stop self-reporting loops
      AND dr.path NOT LIKE '%' || e.uuid || '%'        -- Cycle check
      AND dr.depth < 10                                 -- Depth cap
)
-- Upward chain: full detail (small — typically 3-6 rows)
SELECT 'chain' AS section, depth, name, mail, title, geo, cost_center_desc,
       NULL AS report_count, NULL AS employees, NULL AS contractors,
       (SELECT base_size FROM base_count) AS base_size_checked
FROM upward_chain

UNION ALL

-- Downward reports: summary by level (avoids returning hundreds of individual rows)
SELECT 'reports_summary', depth, NULL, NULL, NULL, NULL, NULL,
       COUNT(DISTINCT uuid),
       COUNT(DISTINCT CASE WHEN employee_type = 'Employee' THEN uuid END),
       COUNT(DISTINCT CASE WHEN employee_type = 'Contingent Worker' THEN uuid END),
       (SELECT base_size FROM base_count)
FROM downward_reports
WHERE depth > 0
GROUP BY depth

QUALIFY ROW_NUMBER() OVER (ORDER BY depth) <= 5000    -- Row safety cap
ORDER BY depth;
```
