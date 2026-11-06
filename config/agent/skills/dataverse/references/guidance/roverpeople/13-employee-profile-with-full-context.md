<!-- roverpeople · from 04-essential-query-templates-1.md -->
### Employee Profile with Full Context
```sql
-- Question: "Get complete profile for ctrielof" or "Show full details for Carl Trieloff"
-- This query returns complete employee profile with manager info and all alignments
-- Tiered matching: exact matches only; last-name fallback ONLY if no exact match.

WITH candidates AS (
    SELECT
        p.uuid, p.name, p.display_name, p.mail, p.title, p.job_role,
        p.employee_type, p.cost_center, p.cost_center_desc, p.geo,
        p.hire_date, p.original_hire_date, p.manager_uuid,
        m.name as manager_name, m.mail as manager_email, m.title as manager_title,
        a.product_alignment, a.role_alignment,
        CASE
            WHEN p.mail ILIKE 'ctrielof@redhat.com' THEN 0    -- Exact email (Tier 0)
            WHEN p.name ILIKE '%Carl%Trieloff%' THEN 0         -- Full name (Tier 0)
            WHEN p.name ILIKE '%Trieloff%Carl%' THEN 0         -- Reversed name (Tier 0)
            ELSE 1                                              -- Last name only (Tier 1)
        END AS match_tier
    FROM roverpeople_db.rhai_marts.rover_people_curr p
    LEFT JOIN roverpeople_db.rhai_marts.rover_people_curr m
        ON p.manager_uuid = m.uuid
    LEFT JOIN roverpeople_db.rhai_marts.rover_alignment_curr a
        ON p.uuid = a.uuid
    WHERE (
           p.mail ILIKE 'ctrielof@redhat.com'     -- Exact kerberos (use @redhat.com, NOT prefix %)
           OR p.name ILIKE '%Carl%Trieloff%'       -- Full name match
           OR p.name ILIKE '%Trieloff%Carl%'       -- Reversed name order
           OR p.name ILIKE '%Trieloff%'            -- Last name fallback (catches nicknames)
    )
)
SELECT uuid, name, display_name, mail, title, job_role, employee_type,
       cost_center, cost_center_desc, geo, hire_date, original_hire_date,
       manager_uuid, manager_name, manager_email, manager_title,
       product_alignment, role_alignment
FROM candidates
WHERE match_tier = (SELECT MIN(match_tier) FROM candidates)
ORDER BY name
LIMIT 10;
```

### Employee with Product Alignment
```sql
SELECT
    p.uuid,
    p.name,
    p.display_name,
    p.mail,
    p.job_role,
    p.cost_center_desc,
    p.geo,
    a.product_alignment,
    a.role_alignment
FROM roverpeople_db.rhai_marts.rover_people_curr p
LEFT JOIN roverpeople_db.rhai_marts.rover_alignment_curr a
    ON p.uuid = a.uuid
ORDER BY p.name;
```
