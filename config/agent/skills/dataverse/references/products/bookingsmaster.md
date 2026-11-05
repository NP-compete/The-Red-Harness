### **Bookingsmaster (BM)**
**Database:** `bookingsmaster_db`

⚠️ **CRITICAL: This is BOOKINGS data, NOT actual revenue data. For revenue queries, use RevenueMaster.**

The comprehensive **bookings analytics** data product (deal pipeline management and sales forecasting) providing:
1. ARR (annual recurring revenue) - a bookings metric, NOT actual recognized revenue
2. ACV (annual Contract value)
3. TCV/TB (Total contract value/ Total booking)
4. ACV plus (annual Contract value includes consumption)
5. ACV plus drawdown (annual Contract value just HCS hybrid committed spend drawdowns)
6. SYB - single year booking is old metric before 2023 and has translated to ACV metric

Specializes in complex business logic for territory/product splits, consumption analysis, and cross-currency financial metrics with validated benchmarks.

**Primary use cases:** Executive bookings reporting, sales performance analysis, pipeline management across global markets.

**When to route here:** Queries about **bookings**, ARR, ACV, **sales performance**, territory analysis, bookings by product, bookings by customer, deal pipeline, and sales forecasting.

**❌ DO NOT route here for:**
- ⚠️ **ANY revenue questions** (actual revenue, recognized revenue, GL revenue, revenue reporting, revenue forecasting, revenue planning, revenue by geography, service revenue, subscription revenue, revenue components, revenue under contract) → Use **RevenueMaster** instead
- Bookingsmaster is for **bookings/ARR/ACV** (what was sold/contracted), NOT revenue (what was recognized)

**Data Scope & Coverage:**

*What IS in Bookingsmaster:*
- Bookings/opportunities data: ACV (Annual Contract Value), ARR (Annual Recurring Revenue), ACV+ (includes consumption premium)
- Current/live data via `pipeline_transactions_acv/arr` tables
- Historical point-in-time/Bookings data via `eoq_transaction_acv/arr_snapshot` tables (695M+ records)
- Financial metrics with multi-currency support (USD conversions via `*_usd_cy_pr` fields)
- Deal pipeline management with stages (Discover, Engage, Validate, Propose, Negotiate)
- Territory splits
- Geographic hierarchy: Super Geo → Geo → Region → Subregion → Coverage Segment → Coverage Subsegment → "pod" → Territory (APAC, EMEA, NA, LATAM, TELCO, ALLIANCES)
- Product hierarchy: Offering Catagory/family → Offering Group -> "Offering line" -> Product SKU
- Customer hierarchies: MDM Party mapping - Sales Group and Global Sales Group
- Partner relationships and channel attribution
- Consumption analysis
- product splits
- Route-to-market classifications and fulfillment channels
- hybrid committed spend deals - commitments/drawdowns
- Essential committed spend deals - commitments/drawdowns
_ Transaction types: New business, renewals, expansions, all Bookings from all sources (Direct/Distributor/Resellers/Web/Training/CCSP/OEM/Private offers etc)
- Various Deal types: Sales led, B2B, Credits/Rebooks, Cloudpaks, MDFs, Royalties, Webstore, Training Orders, market place bookings, private offers, Committed spend deals and drawdowns etc.
- Fiscal quarter-based reporting (Q1: Jan-Mar, Q2: Apr-Jun, Q3: Jul-Sep, Q4: Oct-Dec)

*What IS NOT in Bookingsmaster:*
- ❌ **Actual revenue / recognized revenue / GL revenue** → Use **RevenueMaster**
- ❌ **Revenue reporting, revenue forecasting, revenue by geography** → Use **RevenueMaster**
- ❌ **Service revenue, subscription revenue, revenue components** → Use **RevenueMaster**
- New/renewals/NVR(new vs renewals) metrics
- Not to be used for discounting related enquaries
- Not to be used for sales planning
- Not to be used for Targets or MJ (Manager judgement)
- Not to be used for EBS (oracle enterprice business suite) orders or contract

**🔑 KEY DISTINCTION - Bookings vs. Revenue:**
- **"Show me bookings/ARR/ACV for Q2"** → **Bookingsmaster** (what was sold/contracted)
- **"Show me revenue for Q2"** → **RevenueMaster** (what was recognized as revenue per GL)
- ⚠️ **CRITICAL**: If the query contains the word **"revenue"** in any form, route to **RevenueMaster**, NOT Bookingsmaster
- Bookingsmaster = Bookings/ARR/ACV (sales transactions, what customers bought)
- RevenueMaster = Revenue (recognized revenue from GL, actual financial performance)


**Data Sources:**
Bookingsmaster integrates data from the following source-aligned data products:
- **bookings_db** (staging tables)
- **sfsales.sfsales_marts** - Salesforce sales data and legacy CRM data
- **mdmproduct_db.harbor_marts** - Master data management for products
- **mdmparty_db.partylens_marts** - Master data management for parties
- **enterpriseshared_db.marts** - Shared enterprise data (dates, currencies, etc.)
- **Orders_DB.marts** - Enriched order data product

---

## Table guidance — two reads, found by search

`references/guidance/bookingsmaster/` holds 52 files, one rule or one
query template each, named for what it covers.

1. **`references/guidance/bookingsmaster/00-always-apply.md`** — the
   filters and exclusions that apply to every query against this
   product. Skipping it is how a statement runs clean and returns
   the wrong number.
2. **`grep` the directory for the business term, column or metric
   in the question** — "closed booking flag", "cost center
   hierarchy", "ACV_PLUS", "variance" — then read the one or two
   files that match. `glob` it instead if you would rather scan
   the names.

Never read the directory through. The query templates are working
SQL carrying the business filters that make the numbers correct;
adapt the closest one rather than writing fresh.
