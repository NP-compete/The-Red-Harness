<!-- roverpeople · from 08-essential-query-templates-5.md -->
'LATAM' THEN 'Latin America'
           ELSE COALESCE(geo, 'Unknown')
       END as metric_name,
       CAST(COUNT(*) AS VARCHAR) || ' employees' as metric_value,
       ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) || '% of team' as additional_detail
FROM direct_reports_raw
GROUP BY geo

UNION ALL

-- Cost center breakdown with names
SELECT 'COST CENTER' as section,
       cost_center || ' - ' || cost_center_desc as metric_name,
       CAST(COUNT(*) AS VARCHAR) || ' employees' as metric_value,
       LISTAGG(DISTINCT name, ', ') WITHIN GROUP (ORDER BY name) as additional_detail
FROM direct_reports_raw
GROUP BY cost_center, cost_center_desc

UNION ALL

-- Role alignments (parsed from comma-separated)
SELECT 'ROLE ALIGNMENTS' as section,
       TRIM(role.value) as metric_name,
       CAST(COUNT(DISTINCT dr.uuid) AS VARCHAR) || ' people' as metric_value,
       'Functional alignment' as additional_detail
FROM direct_reports_raw dr
CROSS JOIN LATERAL SPLIT_TO_TABLE(dr.role_alignment, ',') as role
WHERE dr.role_alignment != ''
GROUP BY TRIM(role.value)

UNION ALL

-- Product alignments (parsed from comma-separated)
SELECT 'PRODUCT ALIGNMENTS' as section,
       TRIM(product.value) as metric_name,
       CAST(COUNT(DISTINCT dr.uuid) AS VARCHAR) || ' people' as metric_value,
       ROUND(COUNT(DISTINCT dr.uuid) * 100.0 / (SELECT COUNT(*) FROM direct_reports_raw), 1) || '% of team' as additional_detail
FROM direct_reports_raw dr
CROSS JOIN LATERAL SPLIT_TO_TABLE(dr.product_alignment, ',') as product
WHERE dr.product_alignment != ''
GROUP BY TRIM(product.value)

ORDER BY
    CASE section
        WHEN 'MANAGER INFO' THEN 1
        WHEN 'TEAM SUMMARY' THEN 2
        WHEN 'GEOGRAPHIC DISTRIBUTION' THEN 3
        WHEN 'COST CENTER' THEN 4
        WHEN 'ROLE ALIGNMENTS' THEN 5
        WHEN 'PRODUCT ALIGNMENTS' THEN 6
    END;
```

```sql
-- Concise Variant (Fast)
-- Question: "Show me direct reports for [Manager Name]" or "Who reports to Jane Smith?"
-- IMPORTANT: Use exact kerberos match (with @redhat.com), NOT prefix match.
-- IMPORTANT: Include last name fallback to handle nicknames.
WITH manager_lookup AS (
    SELECT uuid, name, mail
    FROM roverpeople_db.rhai_marts.rover_people_curr
    WHERE (
           mail ILIKE 'username@redhat.com'            -- Exact kerberos — replace (do NOT use 'username%')
           OR name ILIKE '%Manager Name%'              -- Full name — replace
           OR name ILIKE '%LastName%'                  -- Last name fallback — replace
    )
    QUALIFY ROW_NUMBER() OVER (
        ORDER BY
            CASE WHEN mail ILIKE 'username@redhat.com' THEN 0 ELSE 1 END,
            CASE WHEN name ILIKE '%Manager Name%' THEN 0 ELSE 1 END,
            mail
    ) = 1
)
SELECT
    e.name,
    e.mail,
    e.title,
    e.job_role,
    e.employee_type,
    e.cost_center_desc,
    e.geo,
    a.product_alignment,
    a.role_alignment
FROM roverpeople_db.rhai_marts.rover_people_curr e
CROSS JOIN manager_lookup m
LEFT JOIN roverpeople_db.rhai_marts.rover_alignment_curr a ON e.uuid = a.uuid
WHERE e.manager_uuid = m.uuid AND e.uuid != e.manager_uuid
ORDER BY e.name;
```
