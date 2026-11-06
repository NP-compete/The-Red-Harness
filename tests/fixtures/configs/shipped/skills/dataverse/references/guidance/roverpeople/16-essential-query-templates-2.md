<!-- roverpeople · from 05-essential-query-templates-2.md -->
id
    FROM roverpeople_db.rhai_marts.rover_people_curr
    WHERE (
        name ILIKE '%Manager Name%'          -- Full name — replace (e.g., '%Alex%Johnson%')
        OR name ILIKE '%LastName%'            -- Last name fallback — replace (e.g., '%Johnson%')
    )
    QUALIFY ROW_NUMBER() OVER (
        ORDER BY CASE WHEN name ILIKE '%Manager Name%' THEN 0 ELSE 1 END, uuid
    ) = 1
),
org_tree AS (
    -- Base case: manager
    SELECT
        p.uuid,
        p.name,
        p.mail,
        p.title,
        p.job_role,
        p.employee_type,
        p.cost_center_desc,
        p.geo,
        p.manager_uuid,
        0 AS level,
        CAST(p.uuid AS VARCHAR) AS path
    FROM roverpeople_db.rhai_marts.rover_people_curr p
    JOIN base_manager b ON p.uuid = b.uuid

    UNION ALL

    -- Recursive case: walk downward only
    SELECT
        e.uuid,
        e.name,
        e.mail,
        e.title,
        e.job_role,
        e.employee_type,
        e.cost_center_desc,
        e.geo,
        e.manager_uuid,
        t.level + 1,
        t.path || '>' || e.uuid
    FROM org_tree t
    JOIN roverpeople_db.rhai_marts.rover_people_curr e
        ON e.manager_uuid = t.uuid
    WHERE e.uuid != e.manager_uuid
      AND t.level < 8
      AND t.path NOT LIKE '%' || e.uuid || '%'
)
SELECT
    level,
    CASE
        WHEN level = 0 THEN 'Manager'
        WHEN level = 1 THEN 'Direct Reports'
        WHEN level = 2 THEN 'Level 2 Reports'
        WHEN level = 3 THEN 'Level 3 Reports'
        ELSE 'Level ' || level || ' Reports'
    END AS level_description,
    COUNT(DISTINCT uuid) AS reports_count,
    COUNT(DISTINCT CASE WHEN employee_type = 'Employee' THEN uuid END) AS employees,
    COUNT(DISTINCT CASE WHEN employee_type = 'Contingent Worker' THEN uuid END) AS contractors,
    COUNT(DISTINCT geo) AS regions
FROM org_tree
GROUP BY level
ORDER BY level;
```
