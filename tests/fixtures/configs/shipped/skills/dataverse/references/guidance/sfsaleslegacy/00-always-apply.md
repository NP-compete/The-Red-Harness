<!-- sfsaleslegacy · the rules that apply to every query here -->
# Always apply — sfsaleslegacy

Read this before writing any SQL for this product. Everything
below applies regardless of what the question asks.

## Core Query Generation Rules

### Critical Query Generation Rules
* **Currency Safety**: NEVER sum raw `amount` field for multi-currency analysis. **ALWAYS use `amount_for_skuid_c`** (92.41% coverage, universal USD conversion across all marts) for standardized financial reporting. If conversion unavailable, provide multi-currency breakdown.
* **Mandatory Filters**: Always apply the universal filters `is_deleted = 0` and `_fivetran_active = 1` to all queries, unless the knowledge base specifies an exception (e.g., for certain PSA_MARTS views).
* **Field Reliability Priority**: For opportunity types, prioritize `opportunity_type_c` over `type` field - the custom field is more reliable and comprehensive (captures 2x more records for overlay credits).
* **Geographic Field Hierarchy**: **UNIVERSAL PATTERN across all marts** - use this priority for regional analysis:
  * **1st Choice**: `super_region_c` (100% coverage, values: APAC, EMEA, NA, LATAM, none)
  * **2nd Choice**: `region_c` (99.26% coverage, 40+ distinct regions like Japan, GCG, CE, US, etc.)
  * **3rd Choice**: `country_of_order_c` (99.52% coverage, full country names)
  * **❌ AVOID**: `billing_country_c` (only 23.58% coverage - consistently sparse across all marts)
  * **Marketing Exception**: Uses `opportunity_country_of_order` instead of `country_of_order_c`
* **Accurate Counting**: Use `COUNT(DISTINCT primary_key)` for counting records to prevent duplication (e.g., `COUNT(DISTINCT opportunity_id)`).
* **Case-Insensitive Search**: Use `ILIKE` instead of `LIKE` for text searches to catch all variations (e.g., `a.name ILIKE '%Vodafone%'`).
* **Person-Specific Analysis**: For user/person queries, use separate approaches - avoid UNION of owner + team member as it creates role-based duplicates. Choose **Team Member approach** (comprehensive) OR **Owner-only approach** (focused), not both combined.
* **Partner Relationship Counting**: Distinguish between `COUNT(DISTINCT o.id)` (unique opportunities) vs `COUNT(op.id)` (partner relationships). Same opportunity with multiple partners will be counted once vs multiple times respectively. Use based on business question: "How many deals?" vs "How many partner relationships?"
* **NULL Safety**: Explicitly handle NULL values in calculations using `COALESCE(column, 0)` and prevent division-by-zero errors with `NULLIF(denominator, 0)`.
* **Data Freshness**: Understand and select tables based on data freshness patterns where applicable (e.g., SNAPSHOT vs. LIVE).
* **Credit Processing & Payment Terms**: **CRITICAL BUSINESS LOGIC** - Payment terms are often managed through credit approval workflows, not stored directly on opportunities. For payment terms analysis:
  * **Always check GENERAL_CREDIT table** - payment terms are stored in approved credit records
  * **Credit Stage Filtering**: Use `credit_stage LIKE 'Approved%'` to get only approved payment terms
  * **Temporal Logic**: Use window functions to get most recent credit record per opportunity: `QUALIFY ROW_NUMBER() OVER (PARTITION BY opportunity ORDER BY created_date DESC) = 1`
  * **Business Process Understanding**: Don't assume opportunity fields contain all financial terms - many are managed through separate approval processes
  * **GENERAL_MARTS Required**: Only GENERAL_MARTS contains the GENERAL_CREDIT table for comprehensive payment terms analysis

### Financial Data Handling (CRITICAL)
* **Currency Priority for SFSalesLegacy**:
  * 🥇 **`amount_for_skuid_c`**: Universal USD conversion field (92.41% coverage, accurate conversion rates)
  * 🥈 **Multi-currency breakdown**: When conversion unavailable, show by currency with clear labels
  * 🥉 **Single currency filter**: Last resort - filter for USD only and warn about incomplete data
* **Currency Conversion Validation**: EUR≈1.071, GBP≈1.25 conversion rates in `amount_for_skuid_c`
* **Financial Column Disambiguation**: Always reason through choices like booking_amount vs. recognized_revenue or transaction_date vs. booking_date.
* **Safe Calculations**:
```sql
-- Safe Division
numerator / NULLIF(denominator, 0)

-- Safe Percentage Growth
(COALESCE(current, 0) - COALESCE(previous, 0)) / NULLIF(COALESCE(previous, 0), 0)
```

* **Validation Thresholds**:
  * **Discount %**: Must be between 0-100%.
  * **Growth Rates**: Anything >1000% is suspicious and requires investigation.
  * **Revenue**: Negative values often indicate refunds and should be handled.

### Query Construction Best Practices
* **CTE Structure for Complex Queries**:
```sql
WITH base_data AS (
  -- Select and filter source data
  ),
aggregated_data AS (
  -- Group and aggregate the base data
  )
SELECT * FROM aggregated_data;
```

* **Year-over-Year Analysis**:
```sql
LAG(metric, 1) OVER (PARTITION BY [dimension] ORDER BY [time_period]) AS previous_period_metric
```
