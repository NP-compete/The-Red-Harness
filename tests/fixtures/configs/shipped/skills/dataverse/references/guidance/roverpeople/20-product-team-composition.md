<!-- roverpeople · from 06-essential-query-templates-3.md -->
### Product Team Composition
```sql
-- Product team sizes and composition
SELECT
    TRIM(value) as product_name,
    COUNT(DISTINCT p.uuid) as employee_count,
    COUNT(CASE WHEN p.employee_type = 'Employee' THEN 1 END) as full_time_employees,
    COUNT(CASE WHEN p.employee_type = 'Contingent Worker' THEN 1 END) as contractors,
    COUNT(DISTINCT p.geo) as geographic_regions
FROM roverpeople_db.rhai_marts.rover_people_curr p
JOIN roverpeople_db.rhai_marts.rover_alignment_curr a
    ON p.uuid = a.uuid
CROSS JOIN LATERAL SPLIT_TO_TABLE(a.product_alignment, ',') as products
WHERE a.product_alignment IS NOT NULL  -- Only employees with product alignments
GROUP BY TRIM(value)
ORDER BY employee_count DESC;
```
