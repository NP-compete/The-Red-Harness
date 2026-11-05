### Detecting sales query intent

2. **Detect query intent** - Critical distinction for sales-related queries:
   - **DEFAULT BEHAVIOR:** Sales/bookings/customer/opportunity queries → **Bookingsmaster** (even without "current" keyword)
   - **REVENUE queries** → **RevenueMaster** (takes precedence when "revenue" is mentioned)
   - **Analytical queries** (trends, performance, historical analysis, summaries) → Follow revenue vs. bookings distinction above
   - **Legacy system ONLY** (user explicitly requests to use legacy/old Salesforce system) → **SFSalesLegacy**

   **Keywords that trigger RevenueMaster (HIGHEST PRIORITY - check first):**
   - Revenue: "revenue", "actual revenue", "recognized revenue", "GL revenue"
   - Revenue Components: "revenue breakdown", "revenue components", "firm revenue"
   - Revenue by dimension: "revenue by geo", "service revenue", "subscription revenue"
   - Revenue operations: "revenue reporting", "revenue forecast", "revenue planning"

   **Keywords that trigger Discounting (HIGH PRIORITY - check before Bookingsmaster):**
   - ⚠️ **ONLY route when query explicitly involves discount analysis** - For simple TCV/ACV questions, use Bookingsmaster
   - Discount keywords: "discount", "discount %", "discount percentage", "discount percent", "discounted", "discounting", "discount rate", "discount dollars", "discount $"
   - MSRP keywords: "MSRP", "manufacturer suggested retail price", "list price", "retail price", "MSRP vs TCV", "MSRP vs ACV"
   - Discount analysis: "discount trend", "discount analysis", "high discount", "discount over", "discount threshold", "discount validation"
   - Price comparison: "actual price vs list price", "selling price vs MSRP", "price discount"
   - ⚠️ **DO NOT route simple TCV/ACV queries to Discounting** - only when discount/MSRP context is explicit

   **Keywords that trigger Bookingsmaster (DEFAULT for sales/bookings queries - NOT revenue or discounts):**
   - ⚠️ **NEVER route revenue keywords to Bookingsmaster** - All revenue queries go to RevenueMaster
   - ⚠️ **NEVER route discount analysis to Bookingsmaster** - Discount queries with MSRP context go to Discounting
   - Bookings: "bookings", "ARR", "ACV", "TCV", "ACV+", "sales performance" (but NOT revenue or discount analysis)
   - Sales: "opportunities", "pipeline", "deals" (but NOT revenue or discount analysis)
   - Customers: "account", "customer", "purchasing", "buying behavior" (but NOT revenue or discount analysis)
   - Analytics: "trend", "analysis", "performance", "summary", "breakdown", "history", "YoY" (but NOT revenue or discount analysis)
   - Temporal: "current", "active", "today", "this quarter", "forecast", "historical" (but NOT revenue or discount analysis)
   - Partners: "partner relationships", "channel attribution" (but NOT revenue or discount analysis)
   - Products: "product mix", "payment terms" (but NOT discount analysis)

   **Keywords that trigger SFSalesLegacy (EXPLICIT ONLY - must explicitly request legacy system):**
   - "legacy", "legacy system", "legacy Salesforce", "sfsaleslegacy", "old system"
   - "use legacy data", "query legacy", "from legacy system"
   - User must explicitly state they want to use the old/legacy system

   **Keywords that trigger GTM (RHSC account intelligence — use for RHSC account queries):**
   - Account profile: "account profile", "account intelligence", "account data", "firmographic", "company profile"
   - Red Hat adoption flags: "RHEL customer", "OpenShift customer", "Ansible customer", "uses RHEL", "uses OpenShift", "product flags", "install base", "installed base"
   - Intent: "intent", "intent signals", "buyer intent", "researching", "showing intent", "intent for [product]"
   - Competitive displacement: "competitive", "competitive product", "competitor", "competitive displacement", "competitive takeout"
   - IT Budget (**EXTERNAL COMPANIES - RHSC account context ONLY**): "[company/account] cloud spend", "[company/account] cloud budget", "[company/account] virtualization spend", "[company/account] middleware budget", "[company/account] app dev budget", "[company/account] infrastructure spend"
     - ⚠️ **ONLY for third-party company IT budgets on RHSC accounts (prospecting/competitive analysis)**
     - ⚠️ **NOT for Red Hat's internal vendor spend** → Use **ExpenseMaster** for internal spend questions
   - Revenue potential: "revenue potential", "potential revenue", "platform acceleration", "PAI", "share of wallet", "SOW", "propensity to buy"
   - GTM/prospecting: "go-to-market", "GTM", "prospecting", "prospect", "cross-sell", "upsell", "expansion"
   - Contacts: "marketable contacts", "Marketo contacts", "RHSC contacts"
   - Territory: "territory", "pod", "GEO", "region", "geo filter", "segment filter"
   - Renewal risk: "upcoming renewal", "high risk renewal", "renewal ACV"
   - ⚠️ Use GTM when query is about RHSC account universe. For comparing IT budgets/spend between companies, use **HG Insights**

   **Keywords that trigger HG Insights (market / external IT spend — not Red Hat internal):**
   - IT spend: "IT budget", "IT spend", "infrastructure budget" when **comparing between companies** or market view — not Red Hat GL/actuals/ITPF (→ **ExpenseMaster**)
   - Market analysis: "market penetration", "TAM", "total addressable market", "adoption trends", "trend of adoption"
   - Technographic: "companies using", "product adoption", "installation", "technology stack", "adoption level" (market-wide)
   - Cloud (market): "multi-cloud strategy", "cloud migration", "AWS/Azure/GCP usage" across **companies** — not "Red Hat AWS spend" or cost-center spend (→ **ExpenseMaster**)
   - Industry analysis: "industries with high IT spend", "industries where penetration is low"
   - ⚠️ Bare "AWS" or "IT spend" without context → clarify internal (**ExpenseMaster**) vs external (**GTM** / **HG Insights**)
   - ⚠️ Prospecting, competitive intelligence, RHSC account queries → **GTM** (`GTM_HG_INSIGHTS`), not HG Insights alone

   **Keywords that trigger RevenueMaster (actual revenue/GL data):**
   - Revenue: "actual revenue", "recognized revenue", "GL revenue", "revenue components"
   - Geographic: "revenue by geo", "geographic revenue", "regional revenue"
   - Service/Subscription: "service revenue", "subscription revenue", "revenue under contract"
   - Components: "revenue breakdown", "revenue components", "firm revenue"
   - GL/Financial: "general ledger", "GL adjustments", "RevStream data"
   - Reporting: "revenue reporting", "revenue planning"

   **Keywords that trigger Sales Planning (target planning/allocation and seller quotas):**
   - Targets: "sales targets", "quarterly targets", "annual targets", "target allocation"
   - Planning: "sales planning", "sales plan", "planning period", "quarterization"
   - Target Analysis: "target vs actual", "target attainment", "target distribution"
   - Geographic Targets: "territory targets", "regional targets", "planning geo"
   - CCSP Targets: "CCSP targets", "cloud provider targets", "monthly/yearly targets"
   - Seller Quotas: "seller quota", "quota assignment", "quota by territory", "quota by sales role", "quota coverage", "quota detail", "quota dashboard"
   - Quota Analysis: "quota gap", "quota to minimum", "quota stacking", "quota vs target", "quota allocation", "quota breakdown"
   - Seller Coverage: "seller coverage", "territory assignment", "seller territory", "coverage detail"
