<!-- roverpeople · from 09-business-domain-knowledge.md -->
### Product Team Cross-Functional Analysis
```sql
-- Product teams with role distribution
SELECT
    TRIM(product.value) as product_name,
    TRIM(role.value) as role_name,
    COUNT(DISTINCT p.uuid) as employee_count,
    COUNT(CASE WHEN p.employee_type = 'Employee' THEN 1 END) as full_time_count,
    COUNT(CASE WHEN p.employee_type = 'Contingent Worker' THEN 1 END) as contractor_count,
    COUNT(DISTINCT p.geo) as geographic_regions
FROM roverpeople_db.rhai_marts.rover_people_curr p
JOIN roverpeople_db.rhai_marts.rover_alignment_curr a
    ON p.uuid = a.uuid
CROSS JOIN LATERAL SPLIT_TO_TABLE(a.product_alignment, ',') as product
CROSS JOIN LATERAL SPLIT_TO_TABLE(COALESCE(a.role_alignment, 'Unspecified'), ',') as role
WHERE a.product_alignment IS NOT NULL  -- Only employees with product alignments
GROUP BY product_name, role_name
ORDER BY employee_count DESC, product_name, role_name;
```
