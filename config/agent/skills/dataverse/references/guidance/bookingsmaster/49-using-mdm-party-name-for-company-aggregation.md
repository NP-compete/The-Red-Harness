<!-- bookingsmaster · from 10-common-mistakes-to-avoid.md -->
### 8. ❌ Using mdm_party_name for Company Aggregation

**Wrong** (using mdm_party_name for ARR):
```sql
-- User asks: "What is Walmart's ARR?"
SELECT mdm_party_name, SUM(trx_projected_arr_amount_usd_cy_pr)
FROM pipeline_transactions_arr
WHERE mdm_party_name ILIKE '%Walmart%'  -- WRONG field!
GROUP BY mdm_party_name;
```

**Right**:
```sql
-- Use global_sales_group_name for company-level aggregation
SELECT global_sales_group_name, SUM(trx_projected_arr_amount_usd_cy_pr) as total_arr
FROM pipeline_transactions_arr
WHERE global_sales_group_name ILIKE '%Walmart%'  -- CORRECT field
    AND revenue_recognition_date_fiscal_year_quarter = TO_CHAR(CURRENT_DATE, 'YYYY') || '-Q1'
    AND bookings_flag = 'Y'
    AND trx_closed_booking_flag = 'Y'
    AND trx_origin_system <> 'CRM Order'
    AND trx_projected_arr_amount_usd_cy_pr <> 0
GROUP BY global_sales_group_name;
```

**Account Field Hierarchy**:
1. `global_sales_group_name` - For company totals
2. `sales_group_name` - For sales groups
3. `trx_account_name` - For specific accounts
❌ NEVER use `mdm_party_name`

---
