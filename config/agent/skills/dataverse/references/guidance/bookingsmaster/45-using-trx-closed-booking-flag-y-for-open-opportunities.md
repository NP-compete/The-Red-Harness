<!-- bookingsmaster · from 10-common-mistakes-to-avoid.md -->
### 1. ❌ Using `trx_closed_booking_flag = 'Y'` for Open Opportunities

**Wrong**:
```sql
WHERE bookings_flag = 'Y'
  AND trx_closed_booking_flag = 'Y'  -- This excludes open pipeline!
```

**Right** (for open opportunities):
```sql
WHERE bookings_flag = 'Y'
  AND trx_crm_forecast_category <> 'Omitted'
  -- No filter on trx_closed_booking_flag OR
  -- trx_closed_booking_flag = 'N' for explicitly open only
```

**Key**: `bookings_flag` determines IF it counts as a booking (product rules). `trx_closed_booking_flag` determines IF it's closed or open.

---

### 2. ❌ Forgetting to Exclude 'Omitted' Forecast Category

**Wrong**:
```sql
WHERE bookings_flag = 'Y'
-- Missing: AND trx_crm_forecast_category <> 'Omitted'
```

**Right**:
```sql
WHERE bookings_flag = 'Y'
  AND trx_crm_forecast_category <> 'Omitted'
```

---
