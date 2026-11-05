<!-- bookingsmaster · from 05-validated-query-templates-1.md -->
### Query 6: TCV and ACV+ by Route to Market and Forecast Category

**Business Question**: "What is the TCV and ACV+ for current quarter by route to market?"

```sql
-- ============================================================================
-- TCV AND ACV+ BY ROUTE TO MARKET - CURRENT QUARTER
-- ============================================================================
-- Purpose: Analyze bookings by sales channel and forecast category
-- Business Rules:
--   - Route to market shows how the deal was sourced/fulfilled
--   - Forecast category shows pipeline stage
-- ============================================================================

S
