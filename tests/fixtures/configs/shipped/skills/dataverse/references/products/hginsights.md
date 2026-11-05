### **HGInsights**
**Database:** `hginsights_db`

The HG Insights data product provides comprehensive competitive intelligence and IT spend data to enable data-driven marketing and sales strategies. This data product consolidates **technographic information** about hardware/software installations and IT spending patterns across the market. This is **third-party data** sourced by scraping and processing billions of publicly available digital documents related to an entity's reseller information, technology adoption, press releases, job postings, contracts, lines of credit, and consultant relationships. By applying a variety of data models and data science techniques, HG Insights determines which data points are verifications of a product's installation in a company's environment or indicators of an organization's IT Spend.

**🎯 CRITICAL DISTINCTION - HG Insights vs. Bookingsmaster:**
- **HG Insights** = What products companies are **USING** (market intelligence, technographic data, IT budgets, adoption trends)
- **Bookingsmaster** = What Red Hat products companies **BOUGHT from us** (our sales transactions)
- **Market-level adoption analysis** (trends, penetration) → **HG Insights**
- **Customer-level purchase data** (deals) → **Bookingsmaster**

**Primary use cases:** IT spend/budget comparison between companies, technographic data, Total Addressable Market (TAM) Analysis, and Market Penetration studies.

**When to route here:**
- Queries about **IT spend and IT budgets** by technology category (comparing between companies, NOT specific product/vendor spend)
- Queries about **non-Red Hat software/hardware usage** and adoption (cloud products, partner products)
- **TAM/Market analysis**: "market penetration", "industries with high IT spend", "companies not using Red Hat"
- **Technographic data (market-wide)**: "companies using AWS/Azure/GCP", "multi-cloud strategy", "cloud migration" — when comparing **across the market**, not Red Hat internal ledger spend

**⚠️ ROUTING NOTE:** For prospecting, competitive intelligence, and account-level analysis on RHSC accounts, use **GTM** (which includes HG data via `GTM_HG_INSIGHTS`). Use HG Insights directly only for broad market IT spend/budget comparisons and technographic data.

**⚠️ IMPORTANT USAGE NOTES:**
- **IT Budget Aggregations**: Use RELATIVE SPEND table to avoid double-counting. Only use Absolute Spend if specifically requested (and warn against aggregation)
- **Red Hat Product Analysis**: Always join to Bookingsmaster/SFSALES/MDM - do NOT rely on HG Insights alone for Red Hat customer or install base data
- **Specific Product/Vendor Spend**: HG does not track spend at product/vendor level - match to best IT Budget category (e.g., VMware → Virtualization budget)
- **Partner Data**: Third-party technology install data only, NOT Salesforce Opportunity partners

**Data Scope & Coverage:**

*What IS in HG Insights:*
- **Market-wide** technographic and IT spend intelligence (⚠️ NOT Red Hat Sales Cloud Accounts). For **prospect and competitive intelligence on RHSC accounts**, use **GTM** (`GTM_HG_INSIGHTS`), not HG Insights as the primary route.
- Competitive Software intelligence (by product, vendor name)
- Partner Software or Hardware Intelligence (by product, vendor name) - ⚠️ third-party install data, NOT from Salesforce Opportunities
- **IT spend data by granular technology category** (overall IT Budget, Operating System Spend, Virtualization Spend, etc.) - ⚠️ NOT by specific product or vendor
- Basic firmographics for HG company database (⚠️ mix of prospects and current customers - cannot differentiate Red Hat customers in HG alone)
- General trends for non-Red Hat product adoption, market share
- Technographic data (product installations, cloud usage, technology stack)

**🚨 CRITICAL LIMITATIONS:**
- **IT Budget**: Only by solution category, NOT by specific product/vendor (e.g., cannot get "VMware spend", only "Virtualization budget")
- **HG "Companies"**: Mix of prospects AND current customers - NOT equivalent to Red Hat Sales Cloud Accounts
- **Red Hat Install Base**: NOT comprehensive, accurate, or up-to-date - must join to Bookingsmaster/SFSALES for Red Hat customer data
- **Partner Data**: Third-party technology install data, NOT based on Salesforce Opportunities

*What IS NOT in HG Insights:*
- **Red Hat Sales Cloud Accounts** - HG companies are a mix of prospects and customers, NOT RHSC Accounts → Use **Bookingsmaster**
- **Accurate Red Hat install base** - HG data on Red Hat products is incomplete and not up-to-date → Use **Bookingsmaster** for Red Hat customer analysis
- **IT spend by specific product/vendor** - Only by technology category (e.g., cannot get "VMware spend", only "Virtualization budget")
- Red Hat sales transaction data (ARR, ACV, bookings) → Use **Bookingsmaster**
- Red Hat customer purchase history → Use **Bookingsmaster**
- Red Hat customer revenue → Use **Revenuemaster**
- Red Hat opportunity and pipeline data → Use **Bookingsmaster**
- Red Hat Sales Cloud identifiers like Segment, Geo, Territory, Pod → Use **Bookingsmaster**
- Contract or Renewal information on non-Red Hat products
- Pricing information on non-Red Hat products
- Official Market Share or Financial reporting from Gartner, IDC, etc.
- Red Hat Opportunity data including Partners on Red Hat Opportunities (e.g. Financial Partners, Resellers, Distributors, Partner Tier) → Use **Bookingsmaster**
- Salesforce Opportunity partner data - HG partner data is third-party install data only

**🔑 KEY ROUTING RULES:**
- If asking about **comparing IT budgets/spend between companies** → **HG Insights**
- If asking about **RHSC account information** (product flags, intent, competitive footprint) → **GTM** (uses `GTM_HG_INSIGHTS` for competitive/technographic data matched to RHSC accounts)
- If asking "What did customers BUY from Red Hat?" → **Bookingsmaster** (sales data)
- If asking about **Red Hat customers or Red Hat product analysis** → **Must use Bookingsmaster**, NOT HG Insights alone
- If user needs **IT spend for specific product/vendor** → Inform them HG only has category-level budgets, suggest best matching category

---
