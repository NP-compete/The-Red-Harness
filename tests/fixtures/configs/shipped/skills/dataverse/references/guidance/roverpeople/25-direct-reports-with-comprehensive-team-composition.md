<!-- roverpeople · from 07-essential-query-templates-4.md -->
### Direct Reports with Comprehensive Team Composition
```sql
-- Full Analytics (Detailed - preserved)
-- Question: "Get direct reports for Jane Smith" or "Show me who reports to Jane Smith"
-- IMPORTANT: This query automatically includes comprehensive team analytics even if not explicitly requested
-- Analytics include: geography, cost centers, employee types, product/role alignments, tenure analysis
-- IMPORTANT: Use exact kerberos match (with @redhat.com), NOT prefix match.
-- IMPORTANT: Include last name fallback to handle nicknames.

WITH manager_lookup AS (
    -- Manager lookup: exact mail/kerberos only (do not use mail ILIKE 'user%' - can match wrong person)
    SELECT uuid, name, mail, title
    FROM roverpeople_db.rhai_marts.rover_people_curr
    WHERE (
           mail ILIKE 'jsmith@redhat.com'              -- Exact kerberos — replace (do NOT use 'jsmith%')
           OR name ILIKE '%Jane%Smith%'                -- Full name — replace
           OR name ILIKE '%Smith%'                     -- Last name fallback — replace
    )
    QUALIFY ROW_NUMBER() OVER (
        ORDER BY
            CASE WHEN mail ILIKE 'jsmith@redhat.com' THEN 0 ELSE 1 END,
            CASE WHEN name ILIKE '%Jane%Smith%' THEN 0 ELSE 1 END,
            mail
    ) = 1
),
direct_reports_raw AS (
    -- Get all direct reports with alignments
    SELECT
        e.uuid,
        e.name,
        e.display_name,
        e.mail,
        e.title,
        e.job_role,
        e.employee_type,
        e.cost_center,
        e.cost_center_desc,
        e.geo,
        e.hire_date,
        COALESCE(a.product_alignment, '') as product_alignment,
        COALESCE(a.role_alignment, '') as role_alignment,
        m.name as manager_name,
        m.mail as manager_email,
        m.title as manager_title
    FROM roverpeople_db.rhai_marts.rover_people_curr e
    CROSS JOIN manager_lookup m
    LEFT JOIN roverpeople_db.rhai_marts.rover_alignment_curr a ON e.uuid = a.uuid
    WHERE e.manager_uuid = m.uuid
      AND e.uuid != e.manager_uuid  -- Exclude self-reports
)
-- Combined output with all insights
SELECT 'MANAGER INFO' as section,
       manager_name as metric_name,
       manager_email as metric_value,
       manager_title as additional_detail
FROM direct_reports_raw
GROUP BY manager_name, manager_email, manager_title

UNION ALL

-- Team summary with tenure analysis
SELECT 'TEAM SUMMARY' as section,
       'Total Direct Reports' as metric_name,
       CAST(COUNT(*) AS VARCHAR) as metric_value,
       'FTE: ' || COUNT(CASE WHEN employee_type = 'Employee' THEN 1 END) ||
       ', Contractors: ' || COUNT(CASE WHEN employee_type = 'Contingent Worker' THEN 1 END) as additional_detail
FROM direct_reports_raw

UNION ALL

SELECT 'TEAM SUMMARY' as section,
       'Average Tenure' as metric_name,
       ROUND(AVG(DATEDIFF(day, hire_date, CURRENT_DATE()) / 365.25), 1) || ' years' as metric_value,
       'Newest: ' || TO_CHAR(MAX(hire_date), 'Mon YYYY') ||
       ', Longest: ' || TO_CHAR(MIN(hire_date), 'Mon YYYY') as additional_detail
FROM direct_reports_raw

UNION ALL

-- Geographic distribution with percentages
SELECT 'GEOGRAPHIC DISTRIBUTION' as section,
       CASE geo
           WHEN 'NA' THEN 'North America'
           WHEN 'EMEA' THEN 'Europe/Middle East/Africa'
           WHEN 'APAC' THEN 'Asia Pacific'
           WHEN
