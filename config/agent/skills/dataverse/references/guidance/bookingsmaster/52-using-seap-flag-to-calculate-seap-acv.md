<!-- bookingsmaster · from 10-common-mistakes-to-avoid.md -->
### 12. ❌ Using SEAP Flag to Calculate SEAP ACV

**Wrong** (returns ~10x inflated value):
```sql
-- Filters SEAP-flagged rows then sums their full ACV+ — WRONG
SELECT SUM(ACV_PLUS_AMOUNT_USD_CY_PR)
FROM BOOKINGSMASTER_DB.MARTS.PIPELINE_TRANSACTIONS_ACV
WHERE TRX_SEAP_FLAG = 'Y'
  AND BOOKINGS_FLAG = 'Y'
```

**Right**:
```sql
-- Sum the SEAP-specific amount column directly
SELECT SUM(TCV_AMOUNT_SEAP_USD_CY_PR)
FROM BOOKINGSMASTER_DB.MARTS.PIPELINE_TRANSACTIONS_ACV
WHERE BOOKINGS_FLAG = 'Y'
  AND TRX_CRM_FORECAST_CATEGORY <> 'Omitted'
  AND TCV_AMOUNT_SEAP_USD_CY_PR <> 0
```

**Key**: SEAP = Subscription Education Awareness Program (not a region). For SEAP ACV, always use `TCV_AMOUNT_SEAP_USD_CY_PR` — SEAP is all ACV so TCV equals ACV. Never filter by `TRX_SEAP_FLAG` and sum `ACV_PLUS_AMOUNT_USD_CY_PR`.

---

## 💡 Best Practices

### 1. Always Default to Current Year/Quarter and Respect Full-Year Requests

- No time period specified → default to **current year/quarter**
- Year only (CY25, FY25, 2025) → full fiscal year: `TRX_DATE_FISCAL_YEAR_NUMBER = 2025`
- CY and FY are interchangeable — both mean the fiscal year

### 2. Always Clarify Company Name

When user asks for specific company ARR/ACV:
- **Step 1**: Show options using `global_sales_group_name` and `account_name`
- **Step 2**: Let user choose which entity they want
- **Step 3**: Use exact name in GROUP BY

**Never**: Use `mdm_party_name` for aggregation.

### 3. Always Use Correct Product Fields

When user asks for specific product:
- **Use**: `product_split_offering_group` (primary)
- **Or**: `product_split_offering_line` (secondary)
- **Never**: `product_description` or `trx_name` with LIKE

### 4. Always Use ACV+ and TCV for Reporting

When user asks for "ACV", use `acv_plus_amount_usd_cy_pr` (ACV+) and `tcv_amount_usd_cy_pr` (TCV). Do **not** include `acv_amount_usd_cy_pr`.

### 2. Comment Your SQL

Always include comments explaining:
- Why specific filters are applied
- What each metric represents
- Any business rules being enforced
