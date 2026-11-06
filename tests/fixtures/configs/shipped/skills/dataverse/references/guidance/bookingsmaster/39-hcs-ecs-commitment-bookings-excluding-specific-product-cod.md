<!-- bookingsmaster · from 07-validated-query-templates-3.md -->
### Query 16: HCS/ECS Commitment Bookings (Excluding Specific Product Codes)

**Business Question**: "How many HCS Commitments were booked in 2026 with no MCT0001 as the product code?" or "Show me ECS Commitments excluding a specific product code"

**⚠️ CRITICAL**: Use `TRX_HYBRID_COMMITTED_SPEND_EVENT_TYPE` to filter HCS or ECS Commitments — NOT `COMMITMENT_TYPE` (which contains Flex/Upfront values). Use `PRODUCT_CODE` for product code filtering (e.g., MCT0001).

```sql
-- ============================================================================
-- HCS/ECS COMMITMENT BOOKINGS - EXCLUDING SPECIFIC PRODUCT CODES
-- ============================================================================
-- Purpose: Count HCS or ECS Commitment opportunities booked in a year,
--          excluding specific product codes (e.g., MCT0001)
-- Business Rules:
--   - TRX_HYBRID_COMMITTED_SPEND_EVENT_TYPE identifies HCS/ECS transactions
--     Valid values: 'HCS Commitment', 'ECS Commitment'
--   - PRODUCT_CODE is the field for product-level filtering (e.g., MCT0001)
--   - bookings_flag = 'Y' for valid bookings
--   - trx_closed_booking_flag = 'Y' for booked (closed) commitments
--   - Use pipeline_transactions_acv for current year, eoq snapshot for historical
-- ============================================================================

-- Example: HCS Commitments booked in 2026 excl
