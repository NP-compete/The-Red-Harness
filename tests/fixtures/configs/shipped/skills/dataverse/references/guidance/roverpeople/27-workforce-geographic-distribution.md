<!-- roverpeople · from 08-essential-query-templates-5.md -->
### Workforce Geographic Distribution
```sql
-- Employee distribution by region and cost center
SELECT
    geo as region,
    cost_center_desc,
    COUNT(*) as employee_count,
    COUNT(CASE WHEN employee_type = 'Employee' THEN 1 END) as employees,
    COUNT(CASE WHEN employee_type = 'Contingent Worker' THEN 1 END) as contractors
FROM roverpeople_db.rhai_marts.rover_people_curr
WHERE geo IS NOT NULL  -- Only employees with geographic data
GROUP BY geo, cost_center_desc
ORDER BY geo, employee_count DESC;
```
