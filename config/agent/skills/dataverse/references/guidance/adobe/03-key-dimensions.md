<!-- adobe · from 01-business-context-domain.md -->
### 6. **Key Dimensions**

- **Geo**: `geo_country`, `geo_region`, `geo_city`, `geo_zip`, `geo_dma`
- **Campaign/Channel**: `post_campaign`, `post_channel`
- **Page**: `first_hit_pagename`, `first_hit_page_url`, `post_evar_1` (SDR Page Name)
- **Device**: `browser`, `os`, `connection_type`, `post_browser_height`, `post_browser_width`
- **Visit flags**: `new_visit`, `daily_visitor`, `hourly_visitor`, `monthly_visitor`

### 7. **Key Metrics**
- **occurrences**:  COUNT(*) as occurrences
- **page_views**:  COUNT(post_pagename) AS page_views
- **unique_visitors**:  COUNT(DISTINCT CONCAT(post_visid_high,post_visid_low) ) AS unique_visitors
- **visits**:  COUNT(DISTINCT CONCAT(post_visid_high, post_visid_low, visit_num, visit_start_time_gmt)) AS visits

### 8. **URL rule**
- **default URL field**: post_evar_18 - Unless a different field is explicitly mentioned in the prompt use post_evar_18 for any prompts involving urls.
---
