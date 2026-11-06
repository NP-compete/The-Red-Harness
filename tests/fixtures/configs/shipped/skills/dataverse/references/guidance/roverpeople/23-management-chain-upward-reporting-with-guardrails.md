<!-- roverpeople · from 07-essential-query-templates-4.md -->
### Management Chain (Upward Reporting with Guardrails)
```sql
-- Guardrails: ILIKE lookup, upward-only, depth cap (5), cycle check, row cap.
-- IMPORTANT: Use exact kerberos match (with @redhat.com), NOT prefix match.
-- IMPORTANT: Include last name fallback to handle nicknames.
WITH target_employee AS (
    SELECT
        uuid,
        name,
        display_name,
        mail,
        title,
        job_role,
        cost_center_desc,
        geo,
        manager_uuid
    FROM roverpeople_db.rhai_marts.rover_people_curr
    WHERE (
        mail ILIKE 'username@redhat.com'           -- Exact kerberos — replace (do NOT use 'username%')
        OR name ILIKE '%Employee Name%'            -- Full name — replace with target
        OR name ILIKE '%LastName%'                 -- Last name fallback — replace
    )
    QUALIFY ROW_NUMBER() OVER (
        ORDER BY
            CASE WHEN mail ILIKE 'username@redhat.com' THEN 0 ELSE 1 END,
            CASE WHEN name ILIKE '%Employee Name%' THEN 0 ELSE 1 END,
            mail
    ) = 1
),
emp_count AS (
    SELECT COUNT(*) AS base_size FROM target_employee
),
management_chain AS (
    SELECT
        uuid,
        name,
        display_name,
        mail,
        title,
        job_role,
        cost_center_desc,
        geo,
        manager_uuid,
        0 AS level,
        CAST(uuid AS VARCHAR) AS path
    FROM target_employee

    UNION ALL

    SELECT
        m.uuid,
        m.name,
        m.display_name,
        m.mail,
        m.title,
        m.job_role,
        m.cost_center_desc,
        m.geo,
        m.manager_uuid,
        mc.level + 1,
        mc.path || '->' || m.uuid
    FROM roverpeople_db.rhai_marts.rover_people_curr m
    JOIN management_chain mc ON m.uuid = mc.manager_uuid
    WHERE mc.path NOT LIKE '%' || m.uuid || '%'
      AND mc.level < 5
)
SELECT
    level,
    name,
    display_name,
    mail,
    title,
    job_role,
    cost_center_desc,
    geo,
    CASE
        WHEN manager_uuid = uuid THEN 'CEO/Executive (Self-reporting)'
        WHEN manager_uuid IS NULL THEN 'Top of hierarchy'
        ELSE 'Reports upward'
    END AS reporting_status,
    (SELECT base_size FROM emp_count) AS base_size_checked
FROM management_chain
QUALIFY ROW_NUMBER() OVER (ORDER BY level) <= 500
ORDER BY level;
```

```sql
-- Concise Variant (Fast)
-- Question: "Who does [Employee Name] report to?" or "Show management chain"
-- IMPORTANT (Snowflake): do NOT put LIMIT directly in the base SELECT of a recursive CTE.
-- Use a subquery + QUALIFY (as shown below) to pick a single starting employee.
-- IMPORTANT: Use exact kerberos match (with @redhat.com), NOT prefix match.
-- IMPORTANT: Include last name fallback to handle nicknames.
WITH RECURSIVE management_chain AS (
    SELECT uuid, name, mail, title, job_role, cost_center_desc, geo,
           manager_uuid, 0 as level, CAST(uuid AS VARCHAR) as path
    FROM (
        SELECT uuid, name, mail, title, job_role, cost_center_desc, geo, manager_uuid
        FROM roverpeople_db.rhai_marts.rover_people_curr
        WHERE (mail ILIKE 'username@redhat.com'       -- Exact kerberos — replace (do NOT use 'username%')
               OR name ILIKE '%Employee Name%'        -- Full name — replace
               OR name ILIKE '%LastName%')             -- Last name fallback — replace
        QUALIFY ROW_NUMBER() OVER (
            ORDER BY
                CASE WHEN mail ILIKE 'username@redhat.com' THEN 0 ELSE 1 END,
                CASE WHEN name ILIKE '%Employee Name%' THEN 0 ELSE 1 END,
                mail
        ) = 1
    )

    UNION ALL

    SELECT m.uuid, m.name, m.mail, m.title, m.job_role, m.cost_center_desc, m.geo,
           m.manager_uuid, mc.level + 1, mc.path || '->' || m.uuid
    FROM roverpeople_db.rhai_marts.rover_people_curr m
    JOIN management_chain mc ON m.uuid = mc.manager_uuid
    WHERE mc.path NOT LIKE '%' || m.uuid || '%' AND mc.level < 5
)
SELECT level, name, mail, title, job_role, cost_center_desc, geo
FROM management_chain
ORDER BY level;
```
