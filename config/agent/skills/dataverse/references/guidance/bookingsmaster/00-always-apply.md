<!-- bookingsmaster · the rules that apply to every query here -->
# Always apply — bookingsmaster

Read this before writing any SQL for this product. Everything
below applies regardless of what the question asks.

## 🔍 Operational Rules

## 🔴 Critical Business Rules (ALWAYS APPLY)

### 2. The Golden Filter: `bookings_flag = 'Y'`

**CRITICAL**: `bookings_flag = 'Y'` is THE most important filter and MUST always be applied.

```sql
-- ALWAYS include this filter
WHERE bookings_flag = 'Y'
```

**Bookings Flag Definition**:

**Excludes Cloud Paks**:
- Cloud Pak transactions are excluded from bookings

**Product Exclusion Filters**:
- Exclude Ceph standalone lines
- Exclude Travel and Expense lines
- Exclude Automation lines

**General Reporting Filters**:
- "Legacy CRM" Opportunity Type exclusion for Bridge, Buffer, Master Claim, NULL
- Opportunity Type exclusion for Customer Satisfaction%
- Opportunity stage = Private Offer Accepted

**HCS Filters**:
- Commitment Type = Optional lines are exlcuded from Bookings

**IBM Internal**:
- Exlcudes IBM Internal Geo Bookings

**NOTE**: This does NOT include the Closed Bookings check

**What bookings_flag Does NOT Do**:
- Does NOT determine if opportunity is open/closed (use `trx_crm_forecast_category` or `trx_status` for that)


**Closed Bookings Flag Definition**:
- Red Hat Sales Cloud (RHSC):
Omni Channel Opportunities: Opportunity stage - Closed Won.
Non-Omni channel opportunites: Based on the Opportunity stage = Closed Won and the CRM Order Status in 'Activated' or 'B2B Closed' or 'Booked' Only. The field to use is trx_closed_bookings_flag ='Y'
- Enriched Orders: All orders are default Closed Booked only
- Legacy CRM: opportunity Stage = Closed Booked


---

### 2. Exclude Omitted Opportunities

```sql
-- ALWAYS exclude omitted opportunities
WHERE bookings_flag = 'Y'
  AND trx_crm_forecast_category <> 'Omitted'
```

**Why**: Omitted opportunities are not counted in bookings. Valid forecast categories are:
- `Pipeline` - Early stage opportunities
- `Commit` - Committed deals
- `Best Case` - Likely to close
- `Closed` - Already closed deals

---

by Sales Group**:
```sql
-- Current/future quarter (PIPELINE_TRANSACTIONS_ARR)
WHERE SALES_GROUP_NAME = 'PORSCHE INFORMATIK'
  AND GLOBAL_SALES_GROUP_NAME = 'Company Name'

-- Historical quarter (EOQ_TRANSACTION_ARR_SNAPSHOT)
WHERE ACCOUNT_SALES_GROUP_NAME = 'PORSCHE INFORMATIK'
  AND ACCOUNT_GLOBAL_SALES_GROUP_NAME = 'Company Name'
```

**EOQ snapshot vs _LIVE (historical table only)**:
- **`ACCOUNT_SALES_GROUP_NAME`** = sales group **as of that quarter** → use for "ARR for Sales Group X in Q1 2025" (period view). This is the default for historical reporting.
- **`ACCOUNT_SALES_GROUP_NAME_LIVE`** = **current** sales group assignment → use only when the user explicitly wants "ARR for accounts that are **today** in Sales Group X" (reassignment since quarter end can change totals significantly). EOQ also has `ACCOUNT_GLOBAL_SALES_GROUP_NAME_LIVE`, `ACCOUNT_TERRITORY_*_LIVE`, etc.
- PIPELINE has no _LIVE columns (current view only).

**ARR by component (optional)**:
- For "ARR by type" (subscription vs support, etc.) use `ARR_TCV_AMOUNT_SUBSCRIPTIONS_USD_CY_PR`, `ARR_TCV_AMOUNT_SUPPORT_USD_CY_PR`, `ARR_TCV_AMOUNT_TRANS_USD_CY_PR`, `ARR_TCV_AMOUNT_RHLS_USD_CY_PR`, `CONSUMPTION_ANNUAL_REVENUE_AMOUNT_USD_CY_PR` (PIPELINE; EOQ has similar where present). Always use `_usd_cy_pr` fields.

**Exclusion flags**:
- `bookings_flag = 'Y'` applies standard product/geo exclusions. For specific analyses, `AUTOMATION_EXCLUSION_FLAG` and `CEPH_EXCLUSION_FLAG` exist on ARR tables.

**ARR-Specific Requirements**:
```sql
-- ARR query template
SELECT SUM(trx_projected_arr_amount_usd_cy_pr) AS total_arr
FROM bookingsmaster_db.marts.pipeline_transactions_arr
WHERE revenue_recognition_date_fiscal_year_quarter = '2025-Q1'  -- ARR time field
  AND bookings_flag = 'Y'
  AND trx_closed_booking_flag = 'Y'
  AND trx_origin_system <> 'CRM Order'              -- REQUIRED for ARR
  AND trx_projected_arr_amount_usd_cy_pr <> 0       -- REQUIRED for ARR
```

**Key Differences**:
- **Column**: `trx_projected_arr_amount_usd_cy_pr` (NOT acv_plus_amount_usd_cy_pr)
- **Time Field**: `revenue_recognition_date_fiscal_year_quarter` (NOT trx_date_fiscal_year_quarter)
- **Required Filter**: `trx_origin_system <> 'CRM Order'`
- **Non-Zero Filter**: ALWAYS filter `trx_projected_arr_amount_usd_cy_pr <> 0`
- **Aggregation**: Simple SUM() - NO de-duplication needed
- **Benchmark**: Q1 2025 ARR ≈ $6.26B

**⚠️ CRITICAL: Annual ARR Logic - ARR is a Point-in-Time Metric**

**ARR for a Year = ARR as of End of Q4 (NOT sum of all quarters)**

When users ask for annual ARR (e.g., "What is 2024 ARR?" or "Show me ARR for 2024"):
- **✅ CORRECT**: Use Q4 of that year (ARR as of end of Q4)
- **❌ WRONG**: Do NOT sum Q1 + Q2 + Q3 + Q4

**Why**: ARR is a point-in-time metric representing the annual recurring revenue at a specific moment. The Q4 value represents the cumulative ARR as of the end of that fiscal year, which is the correct annual ARR figure.

**Example**:
```sql
-- ✅ CORRECT: Annual ARR for 2024 = ARR as of end of Q4 2024
SELECT SUM(trx_projected_arr_amount_usd_cy_pr) AS annual_arr_2024
FROM bookingsmaster_db.marts.eoq_transaction_arr_snapshot
WHERE revenue_recognition_date_fiscal_year_quarter = '2024-Q4'  -- Q4 only!
  AND bookings_flag = 'Y'
  AND trx_closed_booking_flag = 'Y'
  AND trx_origin_system <> 'CRM Order'
  AND trx_projected_arr_amount_usd_cy_pr <> 0;

-- ❌ WRONG: Do NOT sum all quarters
-- WHERE revenue_recognition_date_fiscal_year_quarter IN ('2024-Q1', '2024-Q2', '2024-Q3', '2024-Q4')
```

**Rule**: For annual ARR queries, always use Q4 of the specified year. ARR represents the cumulative recurring revenue position at year-end, not the sum of quarterly additions.
