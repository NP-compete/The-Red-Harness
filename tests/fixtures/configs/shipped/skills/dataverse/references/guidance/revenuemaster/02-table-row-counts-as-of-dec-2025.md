<!-- revenuemaster · from 01-critical-table-volumes-query-performance.md -->
### Table Row Counts (As of Dec 2025)

| Table | Total Rows | Typical Year Filter | Notes |
|-------|-----------|---------------------|-------|
| `MARTS.GO_TO_MARKET_REVENUE` | **~415 million** | ~78 million (2025) | ⚠️ LARGEST TABLE - Always filter early |
| `MARTS.REVENUE_BY_OFFERING` | ~17 million | ~4.3 million (2025) | Product-level splits |
| `MARTS.REVENUE_FOUNDATION_FPA_ADJUSTMENTS` | ~14.7 million | ~3.7 million (2025) | Finance adjustments |
| `MARTS.REVENUE_FOUNDATION` | ~14 million | ~3.5 million (2025) | Core revenue data |
