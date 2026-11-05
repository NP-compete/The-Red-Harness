<!-- roverpeople · from 04-essential-query-templates-1.md -->
### Manager Hierarchy Analysis (Direct Reports Only)
```sql
-- Simple manager-employee relationship analysis
-- CRITICAL: Must exclude self-reports for CEOs/executives who report to themselves
WITH manager_hierarchy AS (
    SELECT
        e.uuid as employee_uuid,
        e.name as employee_name,
        e.mail as employee_email,
        m.uuid as manager_uuid,
        m.name as manager_name,
        m.mail as manager_email,
        e.cost_center_desc,
        e.job_role
    FROM roverpeople_db.rhai_marts.rover_people_curr e
    LEFT JOIN roverpeople_db.rhai_marts.rover_people_curr m
        ON e.manager_uuid = m.uuid
    WHERE e.uuid != e.manager_uuid  -- CRITICAL: Exclude self-reports (CEO issue)
)
SELECT
    manager_name,
    manager_email,
    cost_center_desc,
    COUNT(*) as direct_reports
FROM manager_hierarchy
WHERE manager_uuid IS NOT NULL
GROUP BY manager_name, manager_email, cost_center_desc
ORDER BY direct_reports DESC;
```
