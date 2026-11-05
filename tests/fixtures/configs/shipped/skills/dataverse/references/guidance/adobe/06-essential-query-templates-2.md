<!-- adobe · from 03-essential-query-templates-2.md -->
UNT(*) as occurrences,
   COUNT(post_pagename)  AS page_views,
   COUNT(DISTINCT CONCAT(post_visid_high,post_visid_low) ) AS unique_visitors,
   COUNT(DISTINCT CONCAT(post_visid_high, post_visid_low, visit_num, visit_start_time_gmt)) AS visits
FROM ADOBE_DB.MARTS.ADOBE_MRKTNG a
   WHERE exclude_hit = 0
   AND hit_source = 1
   AND date_day BETWEEN  '2026-01-01' AND '2026-01-31'
GROUP BY post_evar_18
ORDER BY page_views DESC;
```

### Hit Count by Date (Excluding Excluded Hits)

```sql
SELECT
    DATE_TRUNC('day', date_time) as hit_date,
    COUNT(*) as hit_count,
    COUNT(DISTINCT marketing_touchpoint_id) as unique_hits
FROM adobe_db.marts.adobe_mrktng
WHERE exclude_hit = 0
AND hit_source = 1
  AND date_time >= '2025-01-01'
  AND date_time < '2026-01-01'
GROUP BY 1
ORDER BY 1 DESC;
```

### Sessions/Visits by Geo

```sql
SELECT
    geo_country,
    geo_region,
    COUNT(DISTINCT adobe_session_id) as sessions,
    COUNT(DISTINCT marketing_touchpoint_id) as hits
FROM adobe_db.marts.adobe_mrktng
WHERE exclude_hit = 0
AND hit_source = 1
  AND date_time >= '2025-01-01'
  AND date_time < '2026-01-01'
  AND geo_country IS NOT NULL
GROUP BY 1, 2
ORDER BY sessions DESC
LIMIT 100;
```
