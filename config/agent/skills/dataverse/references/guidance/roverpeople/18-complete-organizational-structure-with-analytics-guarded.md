<!-- roverpeople · from 05-essential-query-templates-2.md -->
### Complete Organizational Structure with Analytics (Guarded)
```sql
-- Guardrails: base-size check, ILIKE, depth cap (10), cycle prevention, row caps.
-- IMPORTANT: Include last name fallback to handle nicknames.
WITH base_manager AS (
    SELECT
        uuid,
        name,
        display_name,
        mail,
        title,
        job_role,
        employee_type,
        cost_center_desc,
        geo,
        hire_date,
        manager_uuid
    FROM roverpeople_db.rhai_marts.rover_people_curr
    WHERE (
        name ILIKE '%Carl Trieloff%'              -- Full name — replace with target manager
        OR name ILIKE '%Trieloff%'                 -- Last name fallback — replace
    )
    QUALIFY ROW_NUMBER() OVER (
        ORDER BY CASE WHEN name ILIKE '%Carl Trieloff%' THEN 0 ELSE 1 END, uuid
    ) = 1
),
base_count AS (
    SELECT COUNT(*) AS base_size FROM base_manager
),
org_tree AS (
    -- Base case
    SELECT
        uuid,
        name,
        display_name,
        mail,
        title,
        job_role,
        employee_type,
        cost_center_desc,
        geo,
        hire_date,
        manager_uuid,
        0 AS level,
        CAST(uuid AS VARCHAR) AS path,
        name AS root_manager_name
    FROM base_manager

    UNION ALL

    -- Recursive case: downward only
    SELECT
        e.uuid,
        e.name,
        e.display_name,
        e.mail,
        e.title,
        e.job_role,
        e.employee_type,
        e.cost_center_desc,
        e.geo,
        e.hire_date,
        e.manager_uuid,
        ot.level + 1,
        ot.path || '->' || e.uuid,
        ot.root_manager_name
    FROM roverpeople_db.rhai_marts.rover_people_curr e
    JOIN org_tree ot ON e.manager_uuid = ot.uuid
    WHERE e.uuid != e.manager_uuid
      AND ot.path NOT LIKE '%' || e.uuid || '%'
      AND ot.level < 10
),
analytics AS (
    SELECT
        -- Basic counts
        COUNT(*) - 1 as total_reports,  -- Exclude the manager
        COUNT(CASE WHEN level = 1 THEN 1 END) as direct_reports,
        COUNT(CASE WHEN level > 1 THEN 1 END) as indirect_reports,
        MAX(level) as levels_deep,

        -- Employee type breakdown
        COUNT(CASE WHEN level > 0 AND employee_type = 'Employee' THEN 1 END) as total_employees,
        COUNT(CASE WHEN level > 0 AND employee_type = 'Contingent Worker' THEN 1 END) as total_contractors
    FROM org_tree
),
level_stats AS (
    SELECT
        level,
        COUNT(*) as level_count,
        COUNT(CASE WHEN employee_type = 'Employee' THEN 1 END) as employees,
        COUNT(CASE WHEN employee_type = 'Contingent Worker' THEN 1 END) as contractors
    FROM org_tree
    GROUP BY level
),
geo_stats AS (
    SELECT
        geo,
        COUNT(*) as geo_count,
        LISTAGG(DISTINCT level, ', ') WITHIN GROUP (ORDER BY level) as levels_present
    FROM org_tree
    WHERE level > 0  -- Exclude manager from geographic distribution
    GROUP BY geo
),
cost_center_stats AS (
    SELECT
        cost_center_desc,
        COUNT(*) as cc_count,
        LISTAGG(DISTINCT level, ', ') WITHIN GROUP (ORDER BY level) as levels_present,
        ROW_NUMBER() OVER (ORDER BY COUNT(*) DESC) as rn
    FROM org_tree
    WHERE level > 0  -- Exclude manager
    GROUP BY cost_center_desc
)
-- Combined output with all analytics
SELECT 'MANAGER INFO' as section,
       'Manager' as metric_type,
       name as metric_value,
       mail as detail_1,
       title as detail_2,
       1 as sort_order
FROM org_tree WHERE level = 0

UNION ALL

SELECT 'SPAN OF CONTROL SUMMARY' as section,
       'Total Reports' as metric_type,
       CAST(total_reports AS VARCHAR) as metric_value,
       'Direct: ' || direct_reports as detail_1,
       'Indirect: ' || indirect_reports as detail_2,
       2 as sort_order
FROM analytics

UNION ALL

SELECT 'SPAN OF CONTROL SUMMARY' as section,
       'Organization Depth' as metric_type,
       CAST(levels_deep AS VARCHAR) || ' levels' as metric_value,
       'From manager to lowest level' as detail_1,
       NULL as detail_2,
       3 as sort_order
FROM analytics

UNION ALL

SELECT 'SPAN OF CONTROL SUMMARY' as section,
       'Employment Types' as metric_type,
       'Total: ' || (total_employees + total_contractors) as metric_value,
       'Employees: ' || total_employees as detail_1,
       'Contractors: ' || total_contractors as detail_2,
       4 as sort_order
FROM analytics

UNION ALL

-- Level breakdown
SELECT 'LEVEL BREAKDOWN' as section,
       'Level ' || level || ' (' ||
       CASE
           WHEN level = 0 THEN 'Manager'
           WHEN level = 1 THEN 'Direct Reports'
           ELSE 'Indirect Reports'
       END || ')' as metric_type,
       CAST(level_count AS VARCHAR) || ' people' as metric_value,
       'Employees: ' || employees as detail_1,
       'Contractors: ' || contractors as detail_2,
       10 + level as sort_order
FROM level_stats

UNION ALL

-- Geographic distribution
SELECT 'GEOGRAPHIC DISTRIBUTION' as section,
       CASE geo
           WHEN 'NA' THEN 'North America'
           WHEN 'EMEA' THEN 'Europe/Middle East/Africa'
           WHEN 'APAC' THEN 'Asia Pacific'
           WHEN 'LATAM' THEN 'Latin America'
           ELSE 'Unknown/Other'
       END as metric_type,
       CAST(geo_count AS VARCHAR) || ' people' as metric_value,
       ROUND(geo_count * 100.0 / SUM(geo_count) OVER(), 1) || '% of org' as detail_1,
       'Across levels: ' || levels_present as detail_2,
       20 as sort_order
FROM geo_stats

UNION ALL

-- Cost Center Distribution (top 10)
SELECT 'COST CENTER DISTRIBUTION' as section,
       cost_center_desc as metric_type,
       CAST(cc_count AS VARCHAR) || ' people' as metric_value,
       'Levels: ' || levels_present as detail_1,
       ROUND(cc_count * 100.0 / SUM(cc_count) OVER(), 1) || '% of org' as detail_2,
       30 + rn as sort_order
FROM cost_center_stats
WHERE rn <= 10

QUALIFY ROW_NUMBER() OVER (ORDER BY sort_order) <= 5000
ORDER BY sort_order;
```

```sql
-- Concise Variant (Fast)
-- Question: "Get organizational structure for [Manager Name]" or "Show me org chart"
-- Guardrails: ILIKE lookup, depth cap (10), cycle check, DISTINCT counts.
-- IMPORTANT: Include last name
