### **MDMPRODUCT**
**Database:** `mdmproduct_db`

MDMPRODUCT (Harbor) is the source-aligned product master for Red Hat — the authoritative "golden record" for all offerings/SKUs. It covers product and offering definitions, pricing foundations (MSRP, List Price), parent/child SKU hierarchy, quoting tiers, offering classifications, and business unit attribution.

**Primary use cases:** SKU lookup and profiling, product pricing analysis, product hierarchy navigation, catalog views by business unit or offering program, product launch/modification tracking, MSRP validation, and regional pricing analysis.

**When to route here:** Queries about MDM product, Harbor product, SKU, SKU hierarchy, product pricing, MSRP, list price, product master data, quoting tier, offering group, or business unit ownership of products.

**❌ DO NOT route here for:**
- **Bookings, ARR, ACV, pipeline, opportunities** → Use **Bookingsmaster**
- **Recognized revenue** → Use **RevenueMaster**
- **Product catalog (official corporate catalog, product portfolios, aliases, components)** → Use **Official Product List**
- **Discount analysis, MSRP vs TCV comparison** → Use **Discounting**
- **Customer/party master data** → Use **MDMPARTY**

**Data Scope & Coverage:**

*What IS in MDMPRODUCT:*
- SKU master data and product attributes
- Parent/child SKU hierarchy and replacement SKUs
- Product lifecycle (availability, end-of-life)
- MSRP and List Price by currency and region
- Quoting tier eligibility
- Business unit attribution (up to 6 levels)
- Technical specifications and service/subscription attributes

*What IS NOT in MDMPRODUCT:*
- Bookings, sales pipeline, or revenue data
- Official corporate product catalog (portfolios, aliases, components)
- Discount calculations or MSRP vs TCV analysis
- Customer or party master data

---
