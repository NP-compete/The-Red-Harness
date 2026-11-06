### **Discounting**
**Database:** `discounting_db`

⚠️ **CRITICAL: This is DISCOUNT ANALYSIS data (MSRP vs TCV/ACV), NOT general bookings or revenue data. For simple TCV/ACV questions without discount context, use Bookingsmaster.**

Comprehensive discount analytics data product providing line-level and opportunity-level discount calculations, MSRP (Manufacturer's Suggested Retail Price) comparisons, and discount validation for Red Hat's sales transactions.

Specializes in discount percentage calculations, high-discount deal identification, discount trends analysis, and discount compliance monitoring across products, geographies, and customer segments.

**Primary use cases:** Discount analysis and monitoring, MSRP vs TCV comparison, high-discount deal identification, discount trend analysis by product/geo/time, discount compliance tracking, and line-item discount breakdowns.

**When to route here:** Queries about discount percentages, MSRP pricing, discount dollars, deals with high discounts, discount trends, discount validation, or any analysis comparing MSRP to actual selling price (TCV/ACV).

**✅ ROUTE HERE when query contains:**
- **Discount keywords:** "discount", "discount %", "discount percentage", "discount percent", "discounted", "discounting"
- **MSRP keywords:** "MSRP", "manufacturer suggested retail price", "list price vs actual", "retail price"
- **Discount analysis:** "discount trend", "discount rate", "discount analysis", "discount dollars", "discount $"
- **High discount queries:** "high discount", "deals over X% discount", "excessive discount", "discount threshold"
- **Price comparison:** "MSRP vs TCV", "MSRP vs ACV", "actual price vs list price"
- **Discount validation:** "valid discount", "invalid discount", "discount outliers"

**❌ DO NOT route here for:**
- **Simple TCV/ACV questions without discount context** → Use **Bookingsmaster** (discounting data is pre-filtered for discount analysis)
- **General bookings questions** → Use **Bookingsmaster** (e.g., "What is total TCV for EMEA?")
- **Revenue data** → Use **RevenueMaster**
- **Sales targets or quotas** → Use **Sales Planning**
- **Sales compensation** → Use **SI Execution**

**🔑 KEY DISTINCTION - Discounting vs. Bookingsmaster:**
- **"What is the discount percentage for RHEL in Q2?"** → **Discounting** (discount analysis with MSRP context)
- **"What is total TCV for RHEL in Q2?"** → **Bookingsmaster** (general bookings, no discount context)
- **"Show me deals with discount over 80%"** → **Discounting** (discount-specific analysis)
- **"Show me top deals by TCV"** → **Bookingsmaster** (general bookings query)
- ⚠️ **CRITICAL**: Only route to Discounting when the query explicitly involves discount analysis, MSRP comparison, or discount-related metrics

**Data Scope & Coverage:**

*What IS in Discounting:*
- Line-level and opportunity-level discount calculations
- MSRP (Manufacturer's Suggested Retail Price) for all products
- TCV, ACV, and ACV+ amounts for discount comparison
- Discount percentage and discount dollar calculations
- Discount validation flags (VALID/INVALID) for quality filtering
- Historical bookings discounts (closed/won deals)
- Current pipeline discounts (open opportunities)
- Product hierarchy for discount analysis (Offering Group → Line → Category)
- Geographic hierarchy for regional discount trends (Geo → Region → Subregion → Pod)
- Line-item product details (Product Code, Description, SKU)
- Opportunity metadata (Number, Name, Close Date, Forecast Category)
- Account information (ID, Name, Global Sales Group)
- Multi-currency support with USD conversions

*What IS NOT in Discounting:*
- **Complete TCV/ACV data for non-discount queries** → Use **Bookingsmaster** (discounting is pre-filtered)
- **Revenue recognition data** → Use **RevenueMaster**
- **Sales targets** → Use **Sales Planning**
- **Sales compensation or quota data** → Use **SI Execution** or **Sales Planning**
- **Customer or account master data** → Use **Bookingsmaster**
- **Pipeline without discount context** → Use **Bookingsmaster**

**🔑 KEY BUSINESS RULES:**
1. **Golden Filter:** Use `LINE_LEVEL_DISCOUNT_VALID = 'VALID'` for product-level aggregations (excludes outliers between -75% and +90%)
2. **Exception:** Do NOT apply validity filter when showing line-item details for a specific opportunity
3. **Discount Formula:** `1 - (TCV / NULLIFZERO(MSRP))` for percentage, `MSRP - TCV` for dollars
4. **Always use NULLIFZERO()** in denominators to prevent division errors
5. **Default to current year/quarter** when time period not specified
6. **Currency:** Always use `*_usd_cy_pr` fields for consistent USD values

**Data Sources:**
Discounting integrates data from the following source-aligned data products:
- **bookings_db** - Historical bookings transactions
- **sfsales_db** - Salesforce opportunities and pipeline
- **mdmproduct_db** - Product master data and MSRP pricing
- **enterpriseshared_db** - Date dimensions and exchange rates

---

## Spend routing: internal vs external (ExpenseMaster, GTM, HG Insights)

**Apply this before matching vendor or cloud keywords alone (e.g. AWS, Azure, GCP).**

| Spend intent | Route | Database |
|--------------|--------|----------|
| **Internal** — Red Hat corporate / IT: GL, OneStream actuals, ITPF/TBM forecast, cost centers, PO/contract impact, booked or projected **RH vendor spend** | **ExpenseMaster** | `expensemaster_db` |
| **External — account** — RHSC prospecting, intent, competitive footprint, modeled IT budget on **known sales accounts** | **GTM** | `gtm_db` (often `GTM_HG_INSIGHTS`) |
| **External — market** — Compare IT spend **between companies**, TAM, market penetration, market technographics | **HG Insights** | `hginsights_db` |

**Ambiguous queries** (e.g. *"how much spend in AWS"* with no internal vs external context): offer **ExpenseMaster** (Red Hat internal) **and** **GTM/HG Insights** (external/account or market), or ask the user to clarify. **Do not** route vendor-only spend questions to GTM or HG Insights by default.

**Vendor names (AWS, Azure, GCP, Dell, Microsoft, VMware):**
- **Internal RH** — "Red Hat AWS spend", "AWS spend last quarter", "AWS by cost center", "AWS GL spend", "AWS forecast (ITPF)" → **ExpenseMaster**
- **RHSC account / territory / prospect** — "AWS adoption in my territory", "competitive Azure at account X", "accounts using Google Cloud" → **GTM**
- **Market / cross-company** — "companies using AWS", "compare Cloud Services IT budget Company A vs B" → **HG Insights** (category-level IT budget only—not vendor/product spend approximations)

---
