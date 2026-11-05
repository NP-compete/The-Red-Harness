<!-- bookingsmaster · from 03-critical-business-rules-always-apply-2.md -->
### 9. Services Terminology (GPS/GLS — Consulting & Training)

**CRITICAL**: When users ask about **GPS**, **GLS**, **Consulting**, or **Training** bookings, use the `PRODUCT_OFFERING_CATEGORY` column with `LIKE` (NOT `=` or `IN`) because multiple subcategories exist under each.

| Term | Meaning | Filter |
|------|---------|--------|
| **GPS** (Global Professional Services) | Consulting | `PRODUCT_OFFERING_CATEGORY LIKE 'CONSULTING%'` |
| **GLS** (Global Learning Services) | Training | `PRODUCT_OFFERING_CATEGORY LIKE 'TRAINING%'` |

**Why LIKE?** The data contains subcategories such as `CONSULTING - FIXED PRICE`, `CONSULTING - TIME & MATERIALS`, `TRAINING - ONLINE LEARNING`, `TRAINING - SUBSCRIPTIONS`, etc. Using exact match (`=` or `IN`) will miss most rows.

**Also applies when users say**: "Services bookings breakdown", "Consulting vs Training", "Services by type"
