<!-- revenuemaster · from 01-critical-table-volumes-query-performance.md -->
### 8. Runrate Calculations (As of Today)
- **ALWAYS** use "as of today" context: `gl_date <= CURRENT_DATE`
- **Check if month is complete**: Compare `DATE_TRUNC('month', gl_date)` with `DATE_TRUNC('month', CURRENT_DATE)`
- **CURRENT month (incomplete)**: EXCLUDE firm revenue - use ONLY other revenue for projection
  - Filter: `is_firm_quarterly = 0 AND is_firm_annually = 0`
  - Reason: Firm revenue already booked on day 1; project variable/usage revenue
- **COMPLETED months**: INCLUDE all revenue (firm + other) for actual runrate
  - Use: `total revenue` (no filtering by firm flags)
  - Reason: Month is complete, use actual total revenue achieved
- **Revenue is front-loaded**: ~90% of monthly revenue books on the 1st day (mostly firm/contracted)
- **Calculation method**:
  - Current month: `Average daily OTHER revenue × 365`
  - Completed month: `Average daily TOTAL revenue × 365` (or `monthly_total × 12`)
- **Start date reference**: December 1st is when monthly subscriptions renew

- Do not report Quarter-over-Quarter (QoQ) changes, growth rates, or trends
- Do use YoY comparisons (e.g., Q2 FY25 vs. Q2 FY24) when discussing revenue performance
- If a user explicitly asks for QoQ figures,  only then show QoQ metric

 Rationale: YoY comparisons account for seasonality and provide a more meaningful picture of business performance for revenue analysis.
---
