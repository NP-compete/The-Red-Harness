<!-- bookingsmaster · from 09-key-column-reference-guide.md -->
### Essential Columns by Use Case

**Opportunity Identification**:
- `TRX_NUMBER` - Opportunity number (primary identifier)
- `trx_name` - Opportunity name
- `trx_status` - Opportunity stage (Discover, Engage, Validate, Propose, Negotiate)
- `trx_crm_forecast_category` - Forecast category (Pipeline, Commit, Best Case, Closed, Omitted)

**Metrics** (ALWAYS use `_usd_cy_pr` fields):
- `acv_plus_amount_usd_cy_pr` - **Always use for ACV reporting**: ACV+ includes consumption
- `tcv_amount_usd_cy_pr` - Total contract value, reported alongside ACV+
- `trx_projected_arr_amount_usd_cy_pr` - **ARR metric** (for ARR tables only). For ARR by type use `ARR_TCV_AMOUNT_SUBSCRIPTIONS_USD_CY_PR`, `ARR_TCV_AMOUNT_SUPPORT_USD_CY_PR`, `ARR_TCV_AMOUNT_TRANS_USD_CY_PR`, `ARR_TCV_AMOUNT_RHLS_USD_CY_PR`, `CONSUMPTION_ANNUAL_REVENUE_AMOUNT_USD_CY_PR` (PIPELINE; EOQ has similar where present).

**Account/Company Identification** (PRIORITY ORDER; column names differ by table):
- **For PIPELINE_TRANSACTIONS_ARR**: `GLOBAL_SALES_GROUP_NAME` (company), `SALES_GROUP_NAME` (sales group)
- **For EOQ_TRANSACTION_ARR_SNAPSHOT**: `ACCOUNT_GLOBAL_SALES_GROUP_NAME` (company), `ACCOUNT_SALES_GROUP_NAME` (sales group). EOQ also has `ACCOUNT_*_LIVE` (e.g. `ACCOUNT_SALES_GROUP_NAME_LIVE`) for **current** assignment; use non-_LIVE for "as of that quarter."
- `trx_account_name` - Individual account name (where applicable)
- ❌ `mdm_party_name` - **NEVER use for ARR/ACV aggregation**
- ⚠️ Using pipeline column names in the EOQ table (or vice versa) causes SQL errors and can inflate results

**Geography**:
- `trx_split_geo` - Geographic region (APAC_APAC, EMEA_EMEA, NA_COMM, NAPS, LATAM, TELCO_TELCO, ALLIANCES_ALLIANCES)
- `trx_split_region` - Region within geo
- `trx_split_territory_name` - Specific territory
- `trx_country_of_order` - **Country name** — use for country-level reporting. Always pair with `trx_split_geo` so Telco geo portions are visible. See Rule 4b.
- **Telco (TELCO_TELCO)**: When reporting on Telco, **always** break down by `trx_split_region` and/or `trx_country_of_order`—never return a single aggregated Telco total. See Critical Business Rule 4.

**Product** (PRIORITY ORDER):
- `product_split_offering_group` - **PRIMARY product filter** (RHEL, OPENSHIFT, ANSIBLE, etc.)
- `product_split_offering_line` - Secondary product detail
- `product_split_offering_line_detail` - Tertiary product detail
- `PRODUCT_OFFERING_CATEGORY` - **For Consulting/Training (GPS/GLS) queries** — use with `LIKE 'CONSULTING%'` or `LIKE 'TRAINING%'` (subcategories exist, never use exact match)
- ❌ `product_description` - **NEVER use with LIKE/CONTAINS** (unreliable)
- **Note**: NULL `product_split_offering_group` typically indicates Discover stage

**HCS/ECS (Hybrid/Enterprise Committed Spend)**:
- `TRX_HYBRID_COMMITTED_SPEND_EVENT_TYPE` - **PRIMARY filter for HCS/ECS**: 'HCS Commitment', 'ECS Commitment'
- `PRODUCT_CODE` - Product code for line-level filtering (e.g., MCT0001)
- `HCS_COMMITMENT_CONTRACT_ID` - HCS contract identifier
- `HCS_COMMITMENT_OPPORTUNITY_ID` - HCS opportunity identifier
- `HCS_COMMITMENT_FISCAL_YEAR` - Fiscal year of HCS commitment
- `HCS_COMMITMENT_TRANSACTION_NUMBER` - HCS transaction number
- `HCS_COMMITMENT_TRANSACTION_DATE` - HCS transaction date
- `HCS_DRAWDOWN_FLAG` - Indicates HCS drawdown transaction
- `TRX_COMMIT_FLAG` - General commitment flag
- `TRX_DRAWDOWN_FLAG` - General drawdown flag
- `ACV_PLUS_AMOUNT_DRAWDOWN_USD_CY_PR` - Drawdown-specific ACV+ in USD
- `TCV_AMOUNT_COMMIT_USD_CY_PR` - Commitment TCV in USD
- `TCV_AMOUNT_COMMIT_DRAWDOWN_USD_CY_PR` - Commitment drawdown TCV in USD

**Channel**:
- `trx_route_to_market` - Sales channel (Direct, Web/GLS, Distributor, CCSP, OEM)

**Time**:
- `TRX_DATE_FISCAL_YEAR_QUARTER` - For ACV/TCV queries, Format: 'YYYY-QN' (e.g., '2025-Q1')
- `revenue_recognition_date_fiscal_year_quarter` - **For ARR queries**, Format: 'YYYY-QN'
- `TRX_DATE` - Actual transaction/close date
- `snapshot_date` - Snapshot date (for snapshot tables)
- **Default**: Use `TO_CHAR(CURRENT_DATE, 'YYYY')` when year not specified

**Flags**:
- `bookings_flag` - **GOLDEN FILTER**: 'Y' = counts as booking (applies standard exclusions)
- `trx_closed_booking_flag` - 'Y' = closed deal, 'N' = open pipeline
- `trx_crm_forecast_category` - Forecast stage (exclude 'Omitted')
- ARR tables: `AUTOMATION_EXCLUSION_FLAG`, `CEPH_EXCLUSION_FLAG` exist for specific analyses if needed

---

## 🎯 Query Decision Tree
