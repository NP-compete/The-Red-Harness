### **SFSalesLegacy**
**Database:** `sfsaleslegacy_db`

🔴 **LEGACY SALESFORCE SYSTEM - NO ACTIVE FIVETRAN SYNC - FROZEN/STALE DATA WARNING**

**⚠️ CRITICAL ROUTING RULES - READ CAREFULLY:**
- **DO NOT USE** for current/active sales, pipeline, or ANY analytical queries
- **DEFAULT to Bookingsmaster** for ALL sales/customer/booking/opportunity queries
- **ONLY USE** when user explicitly requests to use the legacy system with keywords: "legacy", "legacy system", "sfsaleslegacy", "use legacy data"

🔴 **BUSINESS CONTEXT:** This is a **legacy Salesforce system** with **NO active Fivetran sync**. The data is frozen/stale and represents historical CRM data. While it contains comprehensive Salesforce data (opportunities, accounts, products, partners, etc.), it should NOT be used for current business decisions because the data is not being updated.

**⚠️ Use ONLY when:** User explicitly wants to query the legacy system - they must specify "legacy" or explicitly ask to use the old/historical system

**❌ DO NOT use for (Route to Bookingsmaster instead - active system with live data):**
- **Any sales/customer query WITHOUT explicit "legacy" request** → Default to Bookingsmaster
- **Current/active queries** → "current opportunities", "active pipeline", "today's deals"
- **Revenue** → "quarterly revenue"
- **Bookings analytics** → "total ARR", "sales performance"
- **Customer analysis** → "Vodafone's purchases", "account history", "customer behavior"
- **Historical trends/analytics** → "discount trends", "product mix over time", "YoY growth"
- **Partner analysis** → "partner relationships", "channel attribution"
- **Sales performance** → "team performance", "territory analysis", "rep contributions"
- **Any query containing:** "current", "active", "today", "this quarter", "pipeline", "forecast", "trend", "analysis", "performance", "summary"

**When to route here:** ONLY when query explicitly mentions wanting to use the legacy system - keywords: "legacy", "legacy system", "old system", "legacy Salesforce", "sfsaleslegacy", "use legacy data"

**Data Scope & Coverage:**

🔴 **ROUTING WARNING:** This data is STALE with NO active sync. For ANY sales/customer/opportunity query - including ALL historical analysis and trends - use **Bookingsmaster**. SFSalesLegacy is ONLY when user explicitly requests to use the legacy system.

**Architecture:** 5 specialized mart schemas (GENERAL_MARTS, SFSALES_MARTS, MARKETING_MARTS, ENTERPRISEAPPLICATION_MARTS, PSA_MARTS) containing identical core opportunity data (4.86M records) but with different domain-specific supporting tables and analytical contexts.

*What IS in SFSalesLegacy (Frozen Legacy System):*
- 🔴 **FROZEN SALESFORCE CRM DATA** - Complete Salesforce data but NO ACTIVE SYNC (data is stale)
- **Opportunity data**: 4.86M opportunity records with stages, amounts, close dates, forecasts, pipeline snapshots
- **Account data**: Customer hierarchies, relationships, account addresses, EBS integration
- **Product catalog**: Product lines, SKUs, product mix, pricing (list prices, unit prices)
- **Partner relationships**: Channel attribution, partner account linkages, opportunity partners
- **Lead & Campaign data**: Marketing leads, campaign tracking, campaign members, lead management
- **Professional Services**: Timecards, projects, assignments, budgets, milestones, resource management, billable hours
- **Document management**: Contracts, order forms, attachments, content documents, file versioning
- **CPQ data**: Apttus proposals and quote management (GENERAL_MARTS only)
- **Credit processing**: Payment terms via credit approval workflows (GENERAL_CREDIT table in GENERAL_MARTS)
- **Sales operations**: Opportunity line items, contacts, users, opportunity teams, overlay credits
- **Historical tracking**: Change history, field history, audit trails
- **Geographic data**: Super Region, Region, Country fields for regional analysis
- **Financial data**: Multi-currency support with `amount_for_skuid_c` USD conversions

**Mart-Specific Coverage:**
- **GENERAL_MARTS** (18 views): Universal foundation with unique CPQ, documents, contracts, credit processing
- **SFSALES_MARTS** (9 views): Core sales operations (opportunities, line items, partners, products, contacts)
- **MARKETING_MARTS** (13 views): Business-friendly schema with leads, campaigns, marketing attribution
- **ENTERPRISEAPPLICATION_MARTS** (10 views): Deepest historical coverage (2004+) for comprehensive trends
- **PSA_MARTS** (12 views): Professional Services Automation with timecards, projects, resource management

*What IS NOT in SFSalesLegacy:*
- 🔴 **Current/live data** - No active sync, data is stale
- Active sales pipeline and forecasting → Use **Bookingsmaster** or **Forecasting**
- Current customer insights and analytics → Use **Bookingsmaster**
- ACV and ARR metrics → Use **Bookingsmaster**
- Real-time revenue → Use **Revenuemaster**
- Current subscription data → Use **Bookingsmaster**

---

## Table guidance — two reads, found by search

`references/guidance/sfsaleslegacy/` holds 16 files, one rule or one
query template each, named for what it covers.

1. **`references/guidance/sfsaleslegacy/00-always-apply.md`** — the
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
