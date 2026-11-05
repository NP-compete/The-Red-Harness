<!-- roverpeople · from 06-essential-query-templates-3.md -->
fallback to handle nicknames.
WITH base_manager AS (
    SELECT uuid
    FROM roverpeople_db.rhai_marts.rover_people_curr
    WHERE (
        name ILIKE '%Manager Name%'          -- Full name — replace
        OR name ILIKE '%LastName%'            -- Last name fallback — replace
    )
    QUALIFY ROW_NUMBER() OVER (
        ORDER BY CASE WHEN name ILIKE '%Manager Name%' THEN 0 ELSE 1 END, uuid
    ) = 1
),
org_tree AS (
    SELECT
        p.uuid,
        p.employee_type,
        p.geo,
        p.cost_center_desc,
        p.manager_uuid,
        0 AS level,
        CAST(p.uuid AS VARCHAR) AS path
    FROM roverpeople_db.rhai_marts.rover_people_curr p
    JOIN base_manager b ON p.uuid = b.uuid

    UNION ALL

    SELECT
        e.uuid,
        e.employee_type,
        e.geo,
        e.cost_center_desc,
        e.manager_uuid,
        t.level + 1,
        t.path || '>' || e.uuid
    FROM org_tree t
    JOIN roverpeople_db.rhai_marts.rover_people_curr e
        ON e.manager_uuid = t.uuid
    WHERE e.uuid != e.manager_uuid
      AND t.level < 10
      AND t.path NOT LIKE '%' || e.uuid || '%'
)
SELECT
    COUNT(DISTINCT CASE WHEN level > 0 THEN uuid END) AS total_reports,
    COUNT(DISTINCT CASE WHEN level = 1 THEN uuid END) AS direct_reports,
    MAX(level) AS org_depth,
    COUNT(DISTINCT CASE WHEN level > 0 AND employee_type = 'Employee' THEN uuid END) AS employees,
    COUNT(DISTINCT CASE WHEN level > 0 AND employee_type = 'Contingent Worker' THEN uuid END) AS contractors,
    COUNT(DISTINCT CASE WHEN level > 0 THEN geo END) AS regions,
    COUNT(DISTINCT CASE WHEN level > 0 THEN cost_center_desc END) AS cost_centers
FROM org_tree;
```
