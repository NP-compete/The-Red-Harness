### **RevenueMaster**
**Database:** `revenuemaster_db`

⚠️ **CRITICAL: This is ACTUAL REVENUE data (recognized revenue from GL). For bookings/ARR/ACV, use Bookingsmaster.**

Comprehensive **revenue analytics** data product consolidating RevStream transactional data, General Ledger manual adjustments, and Salesforce CRM bookings to provide holistic revenue reporting, forecasting, and planning capabilities.

This system enables accurate financial reporting and business intelligence across Red Hat's product portfolio with executive-level revenue metrics and go-to-market attributes.

**Primary use cases:** Executive revenue reporting, revenue forecasting, revenue planning, revenue component analysis, geographic revenue analysis, and service vs subscription revenue tracking.

**When to route here:** Queries containing the word **"revenue"** - actual revenue (not bookings), recognized revenue, GL revenue, revenue components, revenue by geography, service revenue, subscription revenue, revenue under contract, or GL-based financial data.

**✅ ROUTE HERE when query contains:** "revenue", "recognized revenue", "actual revenue", "GL revenue", "revenue reporting", "revenue forecast", "revenue planning"

**❌ DO NOT route here for:** Bookings, ARR, ACV, sales performance, pipeline → Use **Bookingsmaster** instead.

**Data Scope & Coverage:**

*What IS in RevenueMaster:*
- RevStream transactional revenue data with GL integration
- General Ledger (GL) manual adjustments and corrections
- Revenue components breakdown (levels 1-3) with source system tracking
- Geographic revenue data with GTM (go-to-market) attributes
- Service vs non-service revenue classification (is_service flag)
- Subscription revenue identification (is_sub flag)
- Internal use revenue tracking (is_internal_use flag)
- Fiscal quarter-based reporting (FYQ format: YYYY-Q#)
- Multi-currency support with current year plan rate conversions
- Historical revenue data for trend analysis
- **Currently in pre-production environment**

*What IS NOT in RevenueMaster:*
- ACV (Annual Contract Value) → Use **Bookingsmaster**
- Cash flow metrics → Not available
- TCV (Total Contract Value) → Use **Bookingsmaster**
- Profit/margin data → Not available
- Causal analysis for revenue changes → Not available
- Customer-level revenue details → To be added
- Added targets, forecasts, external revenue
- Product-level revenue breakdowns → To be added
- ARR (Annual Recurring Revenue) → Use **Bookingsmaster**
- Sales pipeline/opportunities → Use **Bookingsmaster**
- Bookings data → Use **Bookingsmaster**

**Data Sources:**
RevenueMaster integrates data from the following sources:
- RevStream transaction system - Core revenue data
- General Ledger (ERP) - GL adjustments and corrections
- Salesforce CRM - Bookings context and alignment

---

## Table guidance — two reads, found by search

`references/guidance/revenuemaster/` holds 30 files, one rule or one
query template each, named for what it covers.

1. **`references/guidance/revenuemaster/00-always-apply.md`** — the
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
