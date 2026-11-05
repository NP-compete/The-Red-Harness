<!-- bookingsmaster · from 02-critical-business-rules-always-apply-1.md -->
### 4c. Geo / Region / Subregion: Validate the Correct Field Before Filtering

When a user mentions a geo, region, or subregion by name, **look up the value** in `SFSALES_DB.MARTS.TERRITORY` to determine which level it belongs to, then use the matching Bookingsmaster column:

| Territory Level | Lookup Column | Bookingsmaster Filter Column |
|-----------------|---------------|------------------------------|
| Geo             | `GEO`         | `trx_split_geo`              |
| Region          | `REGION`      | `trx_split_region`           |
| Subregion       | `SUBREGION`   | `trx_split_subregion`        |

```sql
-- Step 1: Identify the correct level (run once to validate)
SELECT DISTINCT geo, region, subregion
FROM SFSALES_DB.MARTS.TERRITORY
WHERE geo ILIKE '%<user_value>%'
   OR region ILIKE '%<user_value>%'
   OR subregion ILIKE '%<user_value>%';

-- Step 2: Use the matching column in the bookings query
-- Example: User says "MENA" → lookup shows MENA is a SUBREGION → use trx_split_subregion
WHERE trx_split_subregion = 'MENA'
  AND bookings_flag = 'Y'
```

---

### 5. Currency: ALWAYS Use USD Converted Fields

```sql
-- ALWAYS use *_usd_cy_pr fields
SELECT
    SUM(acv_plus_amount_usd_cy_pr) as total_acv_plus_usd,
    SUM(tcv_amount_usd_cy_pr) as total_tcv_usd
```

**Never use** raw `acv_amount` or `tcv_amount` without `_usd_cy_pr` suffix.

---
