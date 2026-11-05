<!-- roverpeople · from 07-essential-query-templates-4.md -->
anager,
    COUNT(DISTINCT CASE WHEN level > 0 THEN uuid END) AS total_reports,
    COUNT(DISTINCT CASE WHEN level > 0 AND employee_type = 'Employee' THEN uuid END) AS employees,
    COUNT(DISTINCT CASE WHEN level > 0 AND employee_type = 'Contingent Worker' THEN uuid END) AS contractors,
    COUNT(DISTINCT CASE WHEN level > 0 THEN cost_center_desc END) AS cost_centers,
    COUNT(DISTINCT CASE WHEN level > 0 THEN geo END) AS regions
FROM org_tree;
```
