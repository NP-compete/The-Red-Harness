<!-- roverpeople · from 06-essential-query-templates-3.md -->
### Get Organizational Statistics and Metrics
```sql
-- Full Analytics (Detailed - preserved)
-- Question: "Get org stats for Carl Trieloff" or "Show organizational metrics for Engineering department"
-- IMPORTANT: This query automatically includes comprehensive analytics for any query type
-- Supported query types:
-- 1. User/Manager: "Get org stats for Carl Trieloff" (uses recursive CTE for complete organization)
-- 2. Department: "Get stats for Engineering department" or "How many people in Data Development?"
-- 3. Cost Center: "Get metrics for cost center 857"

-- Example 1: User Query (Recursive Organization)
WITH RECURSIVE target_employee AS (
    -- Guardrails:
    -- 1) Use ILIKE (avoid LOWER()/UPPER() on columns).
    -- 2) Anchor recursion to a single person to avoid multiple roots / row explosion.
    -- 3) Include last name fallback to handle nicknames.
    SELECT
        uuid, name, mail, title, job_role, employee_type,
        cost_center, cost_center_desc, geo, hire_date, manager_uuid
    FROM roverpeople_db.rhai_marts.rover_people_curr
    WHERE (
        name ILIKE '%Carl%Trieloff%'               -- Full name — replace with target user
        OR name ILIKE '%Trieloff%'                  -- Last name fallback — replace
    )
    QUALIFY ROW_NUMBER() OVER (
        ORDER BY CASE WHEN name ILIKE '%Carl%Trieloff%' THEN 0 ELSE 1 END, uuid
    ) = 1
),
org_tree AS (
    -- Base case: start at the target user/manager
    SELECT
        p.uuid, p.name, p.mail, p.title, p.job_role, p.employee_type,
        p.cost_center, p.cost_center_desc, p.geo, p.hire_date, p.manager_uuid,
        0 as level, CAST(p.uuid AS VARCHAR) as path
    FROM target_employee p

    UNION ALL

    -- Recursive case: Find all subordinates
    SELECT
        e.uuid, e.name, e.mail, e.title, e.job_role, e.employee_type,
        e.cost_center, e.cost_center_desc, e.geo, e.hire_date, e.manager_uuid,
        ot.level + 1, ot.path || '->' || e.uuid
    FROM roverpeople_db.rhai_marts.rover_people_curr e
    JOIN org_tree ot ON e.manager_uuid = ot.uuid
    WHERE e.uuid != e.manager_uuid  -- Prevent self-reporting loops
      AND ot.path NOT LIKE '%' || e.uuid || '%'  -- Prevent circular references
      AND ot.level < 10
),
base_stats AS (
    SELECT
        -- Basic headcount
        COUNT(*) as total_headcount,
        COUNT(CASE WHEN employee_type = 'Employee' THEN 1 END) as employees,
        COUNT(CASE WHEN employee_type = 'Contingent Worker' THEN 1 END) as contractors,

        -- Geographic breakdown
        COUNT(CASE WHEN geo = 'NA' THEN 1 END) as na_headcount,
        COUNT(CASE WHEN geo = 'EMEA' THEN 1 END) as emea_headcount,
        COUNT(CASE WHEN geo = 'APAC' THEN 1 END) as apac_headcount,
        COUNT(CASE WHEN geo = 'LATAM' THEN 1 END) as latam_headcount,
        COUNT(DISTINCT geo) as geographic_regions,

        -- Role distribution (comprehensive detection)
        COUNT(CASE WHEN COALESCE(job_role, '') ILIKE '%engineer%'
                     OR COALESCE(title, '') ILIKE '%engineer%' THEN 1 END) as engineering_roles,
        COUNT(CASE WHEN COALESCE(job_role, '') ILIKE '%manager%'
                     OR COALESCE(title, '') ILIKE '%manager%'
                     OR COALESCE(title, '') ILIKE '%director%'
                     OR COALESCE(title, '') ILIKE '%vp%'
                     OR COALESCE(title, '') ILIKE '%vice president%'
                     OR COALESCE(title, '') ILIKE '%president%' THEN 1 END) as management_roles,
        COUNT(CASE WHEN COALESCE(job_role, '') ILIKE '%consult%'
                     OR COALESCE(title, '') ILIKE '%consult%' THEN 1 END) as consulting_roles,

        -- Recent hiring activity (last 6 months)
        COUNT(CASE WHEN hire_date >= DATEADD(month, -6, CURRENT_DATE()) THEN 1 END) as recent_hires,

        -- Organizational metrics (for user queries)
        COUNT(DISTINCT cost_center) as unique_cost_centers,
        COUNT(DISTINCT cost_center_desc) as unique_departments,
        COUNT(DISTINCT CASE WHEN level <= 2 THEN uuid END) as unique_managers,
        COUNT(CASE WHEN level = 0 THEN 1 END) as top_level_leaders
    FROM org_tree
)
-- Formatted output for comprehensive statistics
SELECT 'QUERY INFO' as section,
       'Query Details' as metric_category,
       'Carl Trieloff' as metric_name,
       'userid' as metric_value,
       'organizational' as additional_info
FROM dual

UNION ALL

SELECT 'HEADCOUNT SUMMARY' as section,
       'Total Headcount' as metric_category,
       CAST(total_headcount AS VARCHAR) as metric_name,
       'Employees: ' || employees || ' | Contractors: ' || contractors as metric_value,
       'Employee %: ' || ROUND((employees * 100.0 / NULLIF(total_headcount, 0)), 1) ||
       ' | Contractor %: ' || ROUND((contractors * 100.0 / NULLIF(total_headcount, 0)), 1) as additional_info
FROM base_stats

UNION ALL

SELECT 'GEOGRAPHIC DISTRIBUTION' as section,
       'Regional Headcount' as metric_category,
       'Total Regions: ' || geographic_regions as metric_name,
       'NA: ' || na_headcount || ' | EMEA: ' || emea_headcount ||
       ' | APAC: ' || apac_headcount || ' | LATAM: ' || latam_headcount as metric_value,
       CASE
           WHEN total_headcount > 0 THEN
               'Largest: ' ||
               CASE GREATEST(na_headcount, emea_headcount, apac_headcount, latam_headcount)
                   WHEN na_headcount THEN 'North America (' || ROUND(na_headcount * 100.0 / total_headcount, 1) || '%)'
                   WHEN emea_headcount THEN 'EMEA (' || ROUND(emea_headcount * 100.0 / total_headcount, 1) || '%)'
                   WHEN apac_headcount THEN 'Asia Pacific (' || ROUND(apac_headcount * 100.0 / total_headcount, 1) || '%)'
                   WHEN latam_headcount THEN 'Latin America (' || ROUND(latam_headcount * 100.0 / total_headcount, 1) || '%)'
               END
           ELSE 'No geographic data'
       END as additional_info
FROM base_stats

UNION ALL

SELECT 'ROLE DISTRIBUTION' as section,
       'Role Categories' as metric_category,
       'Total Categorized' as metric_name,
       'Engineering: ' || engineering_roles || ' | Management: ' || management_roles ||
       ' | Consulting: ' || consulting_roles as metric_value,
       'Other Roles: ' || (total_headcount - engineering_roles - management_roles - consulting_roles) ||
       ' (' || ROUND((total_headcount - engineering_roles - management_roles - consulting_roles) * 100.0 / NULLIF(total_headcount, 0), 1) || '%)' as additional_info
FROM base_stats

UNION ALL

SELECT 'ORGANIZATIONAL METRICS' as section,
       'Structure Metrics' as metric_category,
       'Organizational Complexity' as metric_name,
       'Cost Centers: ' || unique_cost_centers || ' | Departments: ' || unique_departments as metric_value,
       'Managers (L0-L2): ' || unique_managers || ' | Top Leaders: ' || top_level_leaders ||
       ' | Avg Team Size: ' || ROUND(total_headcount * 1.0 / NULLIF(unique_managers, 0), 1) as additional_info
FROM base_stats

UNION ALL

SELECT 'RECENT ACTIVITY' as section,
       'Hiring Activity' as metric_category,
       'Recent Hires (6 months)' as metric_name,
       CAST(recent_hires AS VARCHAR) || ' new employees' as metric_value,
       ROUND((recent_hires * 100.0 / NULLIF(total_headcount, 0)), 1) || '% of workforce | ' ||
       'Monthly avg: ' || ROUND(recent_hires / 6.0, 1) || ' hires/month' as additional_info
FROM base_stats

ORDER BY
    CASE section
        WHEN 'QUERY INFO' THEN 1
        WHEN 'HEADCOUNT SUMMARY' THEN 2
        WHEN 'GEOGRAPHIC DISTRIBUTION' THEN 3
        WHEN 'ROLE DISTRIBUTION' THEN 4
        WHEN 'ORGANIZATIONAL METRICS' THEN 5
        WHEN 'RECENT ACTIVITY' THEN 6
    END;
```

```sql
-- Concise Variant (Fast)
-- Question: "Get org stats for [Manager Name]" or "Show team metrics"
-- Guardrails: ILIKE lookup, depth cap (10), cycle check, DISTINCT counts.
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
        ot.level + 1,
        ot.path || '>' || e.uuid
    FROM org_tree ot
    JOIN roverpeople_db.rhai_marts.rover_people_curr e
        ON e.manager_uuid = ot.uuid
    WHERE e.uuid != e.manager_uuid
      AND ot.path NOT LIKE '%' || e.uuid || '%'
      AND ot.level < 10
)
SELECT
    COUNT(DISTINCT uuid) AS total_headcount_including_m
