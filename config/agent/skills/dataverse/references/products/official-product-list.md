### **Official Product List**
**Database:** `officialproductlist_db`
**Schema:** `marts`
**Maturity:** AI Experimental

Official Product List serves as the official corporate product catalog for Red Hat. This data product maintains authoritative information about Red Hat products, including product attributes, aliases, components, market lifecycle, partners, portfolios, and references.

**Primary use cases:** Product catalog lookup, product hierarchy navigation, product-portfolio mapping, product lifecycle tracking, partner associations, and reference data for downstream data products.

**When to route here:** Queries about Red Hat product catalog, product attributes, product types, product portfolios, product aliases, product components, product market lifecycle (release/EOL dates), product partners, product references, or official product list.

**Data Scope & Coverage:**

*What IS in Official Product List:*
- Product master data (core product attributes, status)
- Product aliases (alternate names)
- Product components
- Product market lifecycle (release dates, end-of-life)
- Product-portfolio mapping
- Product-partner associations
- Product types and type mapping
- Product references and notes
- Consolidated denormalized `product_details` mart

*What IS NOT in Official Product List:*
- Bookings, ARR, ACV, sales data → Use **Bookingsmaster**
- Revenue data → Use **RevenueMaster**
- MDM product pricing or SKU hierarchy → Use **MDM Product**
- Order or transaction data → Use appropriate transactional data products
- **SKU-level offering lifecycle performance**, leverage/inactivation signals, pipeline-derived ARR at SKU grain → Use **Offering Lifecycle Management (OLM)**

**❌ DO NOT route here for:**
- **OLM**, **offering lifecycle**, **SKU leverage**, **inactivation candidates**, **SKU ARR on the OLM mart**, **quoting tier**, **subscription coverage on OLM** → Use **Offering Lifecycle Management (OLM)**

**KEY ROUTING RULES:**
- **"Product catalog"** / **"Official product list"** / **"Product attributes"** → **Official Product List**
- **"Product lifecycle"** (reference dates, market lifecycle in catalog) / **"Product EOL"** / **"Product release date"** → **Official Product List**
- **"Product portfolio"** / **"Product type"** / **"Product alias"** → **Official Product List**
- **"Product partners"** / **"Product references"** → **Official Product List**

---
