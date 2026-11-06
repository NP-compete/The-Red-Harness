<!-- roverpeople · from 09-business-domain-knowledge.md -->
### Employee Tenure Analysis
```sql
-- Employee tenure categorization and analysis
SELECT
    geo,
    employee_type,
    CASE
        WHEN DATEDIFF(day, hire_date, CURRENT_DATE()) <= 365 THEN 'New (0-1 years)'
        WHEN DATEDIFF(day, hire_date, CURRENT_DATE()) <= 1095 THEN 'Growing (1-3 years)'
        WHEN DATEDIFF(day, hire_date, CURRENT_DATE()) <= 1825 THEN 'Experienced (3-5 years)'
        WHEN DATEDIFF(day, hire_date, CURRENT_DATE()) <= 3650 THEN 'Senior (5-10 years)'
        ELSE 'Veteran (10+ years)'
    END as tenure_category,
    COUNT(*) as employee_count
FROM roverpeople_db.rhai_marts.rover_people_curr
WHERE hire_date IS NOT NULL  -- Only employees with hire date
GROUP BY geo, employee_type, tenure_category
ORDER BY geo, employee_type, tenure_category;
```
