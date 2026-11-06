<!-- adobe · from 03-essential-query-templates-2.md -->
### Campaign Performance

```sql
SELECT
    post_campaign as campaign,
    post_channel as channel,
    DATE_TRUNC('week', date_time) as week,
    COUNT(DISTINCT adobe_session_id) as sessions,
    COUNT(*) as hits
FROM adobe_db.marts.adobe_mrktng
WHERE exclude_hit = 0
AND hit_source = 1
  AND date_time >= '2025-01-01'
  AND post_campaign IS NOT NULL
GROUP BY 1, 2, 3
ORDER BY week DESC, sessions DESC
LIMIT 500;
```

### Page/Content Analysis (post_evar_1 = SDR Page Name)

```sql
SELECT
    post_evar_1 as page_name,
    COUNT(DISTINCT adobe_session_id) as sessions,
    COUNT(post_pagename) as page_views
FROM adobe_db.marts.adobe_mrktng
WHERE exclude_hit = 0
AND hit_source = 1
  AND date_time >= '2025-01-01'
  AND post_evar_1 IS NOT NULL
GROUP BY 1
ORDER BY page_views DESC
LIMIT 100;
```
