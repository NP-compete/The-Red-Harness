<!-- roverpeople · from 09-business-domain-knowledge.md -->
### Manager Team Distribution
```sql
-- Manager span of control analysis
SELECT
    m.name as manager_name,
    m.geo as manager_geo,
    COUNT(e.uuid) as direct_reports,
    COUNT(CASE WHEN e.employee_type = 'Employee' THEN 1 END) as employee_reports,
    COUNT(CASE WHEN e.employee_type = 'Contingent Worker' THEN 1 END) as contractor_reports,
    COUNT(DISTINCT e.geo) as geographic_spread,
    COUNT(DISTINCT e.cost_center_desc) as cost_center_spread
FROM roverpeople_db.rhai_marts.rover_people_curr m
JOIN roverpeople_db.rhai_marts.rover_people_curr e
    ON m.uuid = e.manager_uuid
GROUP BY m.uuid, m.name, m.geo
ORDER BY direct_reports DESC;
```

---

*RoverPeople provides the foundation for Red Hat's workforce management and organizational analytics.*
