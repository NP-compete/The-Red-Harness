<!-- bookingsmaster · from 02-critical-business-rules-always-apply-1.md -->
### 1b. Full-Year Queries: CY25, FY25, or 2025 Mean the Entire Fiscal Year

**CRITICAL**: CY, FY, and bare year numbers (e.g., CY25, FY25, 2025) all mean the **full fiscal year** — do NOT restrict by quarter. CY and FY are interchangeable.

```sql
-- ✅ CORRECT - ACV/TCV: use TRX_DATE_FISCAL_YEAR_NUMBER for full-year queries
WHERE TRX_DATE_FISCAL_YEAR_NUMBER = 2025

-- ✅ CORRECT - ARR: annual ARR = Q4 (point-in-time), so "FY25 ARR" = Q4 2025
WHERE revenue_recognition_date_fiscal_year_quarter = '2025-Q4'

-- ❌ WRONG - Do NOT restrict to a single quarter when user asked for full year
WHERE TRX_DATE_FISCAL_YEAR_QUARTER = '2025-Q1'
```
