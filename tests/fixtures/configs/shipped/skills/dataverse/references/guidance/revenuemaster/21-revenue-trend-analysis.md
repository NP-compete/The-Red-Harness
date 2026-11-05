<!-- revenuemaster · from 03-validated-query-templates-2.md -->
### Revenue Trend Analysis

```sql
-- ============================================================================
-- Year-over-Year Revenue Comparison (Apples-to-Apples) - ⭐ PREFERRED METHOD
-- ============================================================================
-- Business Question: "Show me year-over-year revenue comparison"
--
-- 🎯 **PREFERRED METHOD FOR PERFORMANCE ANALYSIS**: Year-over-Year (YoY) comparisons
-- are the recommended approach for describing revenue performance. YoY comparisons:
-- - Account for seasonal patterns and business cycles
-- - Provide more meaningful growth insights
-- - Avoid misleading quarter-end effects
-- - Enable apples-to-apples comparisons even for incomplete periods
--
-- CRITICAL: Always use apples-to-apples comparison for incomplete periods
-- - If today is Dec 17, 2025, com
