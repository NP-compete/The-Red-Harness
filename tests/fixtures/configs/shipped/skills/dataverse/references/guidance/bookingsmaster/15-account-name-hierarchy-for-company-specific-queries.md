<!-- bookingsmaster · from 03-critical-business-rules-always-apply-2.md -->
### 8. Account Name Hierarchy for Company-Specific Queries

**CRITICAL**: When querying ARR/ACV for a specific company, use the correct account identifier hierarchy.

**Priority Order** (use in this sequence):
1. **`global_sales_group_name`** - Highest level aggregation (recommended for company totals)
2. **`sales_group_name`** - Sales group level
3. **`trx_account_name`** - Individual account level

**❌ NEVER use `mdm_party_name` for ARR/ACV aggregation** - This can cause incorrect totals.

**Best Practice**: Present options to user when company is ambiguous:
```sql
-- Step 1: Show user the available options
SELECT DISTINCT
    global_sales_group_name,
    sales_group_name,
    SUM(trx_projected_arr_amount_usd_cy_pr) as arr_amount
FROM bookingsmaster_db.marts.pipeline_transactions_arr
WHERE (global_sales_group_name ILIKE '%Walmart%'
    OR sales_group_name ILIKE '%Walmart%')
    AND revenue_recognition_date_fiscal_year_quarter = TO_CHAR(CURRENT_DATE, 'YYYY') || '-Q1'
    AND bookings_flag = 'Y'
    AND trx_closed_booking_flag = 'Y'
    AND trx_origin_system <> 'CRM Order'
    AND trx_projected_arr_amount_usd_cy_pr <> 0
GROUP BY global_sales_group_name, sales_group_name
ORDER BY arr_amount DESC;

-- Step 2: User clarifies they want global sales group → Use global_sales_group_name
SELECT
    global_sales_group_name,
    SUM(trx_projected_arr_amount_usd_cy_pr) as total_arr
FROM bookingsmaster_db.marts.pipeline_transactions_arr
WHERE global_sales_group_name = 'Walmart Inc'  -- Exact name after user confirms
    AND revenue_recognition_date_fiscal_year_quarter = TO_CHAR(CURRENT_DATE, 'YYYY') || '-Q1'
    AND bookings_flag = 'Y'
    AND trx_closed_booking_flag = 'Y'
    AND trx_origin_system <> 'CRM Order'
    AND trx_projected_arr_amount_usd_cy_pr <> 0
GROUP BY global_sales_group_name;
```
