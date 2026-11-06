<!-- roverpeople · from 05-essential-query-templates-2.md -->
### Detailed Span of Control Report (Individual Employee Listing with Guardrails)
```sql
-- Guardrails: ILIKE search, depth cap (8), cycle check, and row cap.
-- IMPORTANT: Include last name fallback in WHERE to handle nicknames.
WITH target_manager AS (
    SELECT uuid, name, mail, title, job_role, cost_center_desc, geo, employee_type, manager_uuid
    FROM roverpeople_db.rhai_marts.rover_people_curr
    WHERE (
        name ILIKE '%Target Manager Name%'        -- Full name — replace with actual name
        OR name ILIKE '%LastName%'                 -- Last name fallback — replace with actual last name
    )
    QUALIFY ROW_NUMBER() OVER (
        ORDER BY CASE WHEN name ILIKE '%Target Manager Name%' THEN 0 ELSE 1 END, uuid
    ) = 1
),
target_count AS (
    SELECT COUNT(*) AS base_size FROM target_manager
),
org_tree AS (
    SELECT
        uuid,
        name,
        mail,
        title,
        job_role,
        cost_center_desc,
        geo,
        employee_type,
        manager_uuid,
        0 AS level,
        CAST(uuid AS VARCHAR) AS path
    FROM target_manager

    UNION ALL

    SELECT
        e.uuid,
        e.name,
        e.mail,
        e.title,
        e.job_role,
        e.cost_center_desc,
        e.geo,
        e.employee_type,
        e.manager_uuid,
        t.level + 1,
        t.path || '->' || e.uuid
    FROM roverpeople_db.rhai_marts.rover_people_curr e
    JOIN org_tree t ON e.manager_uuid = t.uuid
    WHERE e.uuid != e.manager_uuid
      AND t.path NOT LIKE '%' || e.uuid || '%'
      AND t.level < 8
)
SELECT
    level,
    name,
    mail,
    title,
    job_role,
    cost_center_desc,
    geo,
    employee_type,
    (SELECT base_size FROM target_count) AS base_size_checked
FROM org_tree
QUALIFY ROW_NUMBER() OVER (ORDER BY level, name) <= 5000
ORDER BY level, name;
```

```sql
-- Concise Variant (Fast)
-- Question: "List all employees under [Manager Name]"
-- Guardrails: ILIKE lookup, depth cap (8), cycle check, row cap.
-- IMPORTANT: Include last name fallback to handle nicknames.
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
SELECT level, name, mail, title, job_role, cost_center_desc, geo, employee_type
FROM org_tree
QUALIFY ROW_NUMBER() OVER (ORDER BY level, name) <= 5000
ORDER BY level, name;
```
