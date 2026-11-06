<!-- jira · from 02-4-advanced-patterns.md -->
### 📈 Multi-Team Sprint Velocity
```sql
-- For projects with parallel team sprints (e.g., DATA project)
WITH sprint_periods AS (
    SELECT
        REGEXP_SUBSTR(name, 'CY[0-9]{2}Q[0-9]SP[0-9]+') as period,
        MIN(TO_TIMESTAMP(start_date/1000)::DATE) as start_date,
        COUNT(DISTINCT name) as team_count,
        SUM(velocity) as total_velocity
    FROM (
        -- Sprint velocity calculation here
    )
    GROUP BY period
    HAVING period IS NOT NULL
)
SELECT * FROM sprint_periods ORDER BY start_date DESC LIMIT 6;
```
