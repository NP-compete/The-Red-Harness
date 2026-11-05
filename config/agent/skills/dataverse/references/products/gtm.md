### **GTM (Go-To-Market Account Data Product)**
**Database:** `gtm_db`
**Maturity:** AI Ready

GTM is the source of truth for first- and third-party **account intelligence** used for demand generation at Red Hat. It stitches signals from firmographics, technographics, intent, behavior, propensity, account scoring, and revenue potential into a unified account profile for ~200K RHSC accounts.

**🎯 CRITICAL DISTINCTION – GTM vs. Bookingsmaster vs. HG Insights:**
- **GTM** = Unified account intelligence layer (Red Hat + third-party signals): firmographics, product flags, intent, revenue potential, competitive tech stack — *for a known Red Hat RHSC account universe*. Competitive/technographic data within GTM comes from the `GTM_HG_INSIGHTS` table (HG data matched to RHSC accounts).
- **Bookingsmaster** = What Red Hat customers **bought** (transactions, ARR, ACV, deals)
- **HG Insights** = IT spend/budget data by technology category and technographic data across the broad market (prospects + customers). Use for comparing IT budgets/spend between companies.

**⚠️ GTM vs. HG Insights routing:**
- If the query is about **RHSC account information** (product flags, intent, revenue potential, competitive footprint for known accounts) → **GTM**
- If the query is about **comparing IT budgets/spend data between companies** → **HG Insights**
- If the user does not have access to HG Insights, try **GTM** for IT budget/spend (via `GTM_HG_INSIGHTS` table), and vice versa

**Primary use cases:** Account profiling, prospecting, audience segmentation, competitive displacement analysis, intent-driven outreach, revenue potential prioritization, cross-sell/upsell targeting, territory planning.

**When to route here:** Queries about account intelligence combining any of: product adoption flags, buyer intent signals, firmographics, competitive tech footprint, IT budgets, and/or revenue potential — *for Red Hat's account universe*.

**✅ Route here when query contains:**
- Account profile: "account profile", "account intelligence", "account data", "firmographic", "company profile"
- Segmentation: "segment", "Fortune 500", "Fortune 1000", "Global 500", "S&P Global", "employee count", "company size", "annual revenue"
- Territory/Geo: "territory", "pod", "region", "geo", "GEO filter"
- IT Budget (RHSC account context): "cloud spend", "cloud budget", "cloud maturity", "virtualization spend", "middleware budget", "app dev budget", "OS spend" — for IT budget/spend on RHSC accounts. For comparing IT budgets between companies, use **HG Insights** instead.
- Technographics: "technology footprint", "product footprint", "installed base", "install base", "tech stack", "technographic", "products installed", "vendor analysis"
- Hyperscalers (RHSC/account context only — not Red Hat internal ledger spend): "VMware", "Oracle", "Microsoft", "AWS", "Azure", "GCP", "CentOS", "AWX" when query is about **external/account** competitive footprint, territory, or prospecting → **GTM**. For **Red Hat internal** AWS/Azure/vendor actuals or forecast → **ExpenseMaster**
- Red Hat adoption: "RHEL customer", "OpenShift customer", "Ansible customer", "uses RHEL", "uses OpenShift", "uses Ansible", "product flags"
- Intent: "intent", "intent signals", "buyer intent", "researching", "showing intent"
- Competition: "competitive", "competitive product", "competitor", "competitive displacement", "competitive takeout"
- Revenue potential: "revenue potential", "potential revenue", "platform acceleration", "PAI", "share of wallet", "SOW", "propensity", "propensity to buy"
- GTM: "go-to-market", "GTM", "prospecting", "prospect", "cross-sell", "upsell", "expansion"
- Contacts: "marketable contacts", "Marketo contacts", "RHSC contacts", "company domain", "upcoming renewal"
- Cloud: "cloud native", "cloud company", "multi-cloud", "hyperscaler", "cloud maturity"

**❌ Do NOT route here when query contains:**
- "bookings", "opportunity", "opportunities", "pipeline", "closed won", "closed lost", "sales performance"
- "discount", "reseller", "distributor", "partner on deal"
- "recognized revenue", "actual revenue", "service revenue", "subscription revenue", "revenue forecast", "revenue planning"
- "quota", "compensation", "sales target", "expense", "profit", "headcount", "budget planning"
- **Internal Red Hat IT forecast, ITPF/TBM, IT actuals, GL, PO/contract impact, IT cost centers** → **ExpenseMaster** — do not use **GTM**; it carries **third-party modeled IT budgets on RHSC accounts** for prospecting, not Snowflake ITPF or ledger actuals
- "org chart", "cost center", "EBS" — when the ask is **internal** finance, ledger, or RH org (not GTM account intelligence) → **ExpenseMaster**, **fammatrix**, **RoverPeople**, or **EBS** as appropriate

**Data Scope & Coverage:**

*What IS in GTM:*
- Account Firmographics and Profile (RHSC account universe, ~200K accounts)
- IT Budget data (modeled estimates by technology category: cloud, OS, virtualization, app dev, hardware)
- Red Hat Product Adoption Flags (40+ product/customer flags: `RHEL_CUSTOMER`, `OPENSHIFT_CUSTOMER`, `ANSIBLE_CUSTOMER`, etc.)
- Buyer Intent Signals (topic research + website visit activity via `GTM_INTENT`)
- Competitive/non-Red Hat Technology Stack (ISVs, hyperscalers via `GTM_HG_INSIGHTS`)
- Revenue Potential and Platform Acceleration Initiative (`REVENUE_POTENTIAL_ACCOUNT_LEVEL`)
- Renewal risk indicators (`HAS_RHEL_HIGH_RISK_RENEWAL_NEXT_12M`, other `HAS_*_RENEWAL_*` flags on `GTM_ACCOUNT`; dollar renewal ACV is not on `GTM_ACCOUNT`—use Bookingsmaster/Renewals per DPO when needed)

*What IS NOT in GTM:*
- **Bookings, ARR, ACV, pipeline transactions** → Use **Bookingsmaster**
- **Recognized revenue, GL revenue** → Use **RevenueMaster**
- **Individual contact PII** → Not included
- **Sales compensation and quotas** → Use **Sales Planning / SI Execution**
- **Internal cost / internal IT spend / internal hyperscaler cloud actuals** → Use **ExpenseMaster** (GL/OneStream, Cloudability mart, or ITPF/TBM per question)
- **IT spend for specific product/vendor level** (e.g., "VMware spend") → IT_BUDGET_* fields are category-level only

**Data Sources:**
GTM integrates data from the following source-aligned data products:
- **HG Insights** – Technographic / competitive product data (joined via DUNS or Domain)
- **Bookingsmaster** – Product customer flags and ARR (cross-product join when needed)
- **MDM Party** – Account identity and hierarchy
- **Profound Networks** – Digital entity resolution and domain data
- **Marketo** – Marketing contact counts
- **Renewals** – Renewal risk flags and ACV

---
