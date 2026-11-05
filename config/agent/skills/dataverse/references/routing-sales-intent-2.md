### Detecting sales query intent (continued)

Continues `routing-sales-intent.md`; read that first.

   **Keywords that trigger Source Data Governance (reference data/standards):**
   - EDS: "enterprise data standards", "EDS code", "EDS standard", "standardized code"
   - Code lookups: "code description", "standard code", "reference code", "lookup code"
   - Industry: "industry hierarchy", "industry classification", "industry vertical", "sub-industry"
   - SIC: "SIC code", "Standard Industrial Classification", "SIC description", "industry code"
   - Reference data: "reference data", "data standards", "code validation", "standardized classification"
   - Data governance: "data governance standards", "standardized reference", "code lookup"

   **Keywords that trigger Official Product List (product catalog):**
   - Product catalog: "product catalog", "official product list", "product list", "product attributes"
   - Product lifecycle (reference): "product lifecycle", "product EOL", "end of life", "product release date" (catalog context)
   - Product structure: "product portfolio", "product type", "product alias", "product components"
   - Product associations: "product partners", "product references", "products by portfolio"
   - ⚠️ **DO NOT route OLM/SKU mart metrics here** — "OLM", "offering lifecycle", "sku_leveraged", "curr_arr on olm_final_data" → **Offering Lifecycle Management (OLM)**

   **Keywords that trigger Offering Lifecycle Management (OLM):**
   - OLM / offering lifecycle: "OLM", "offering lifecycle", "offering lifecycle management", "olm_final_data"
   - SKU status & leverage: "leveraged SKU", "sku_leveraged", "inactivation candidate", "sku_unleveraged", "active SKUs" (catalog status on mart)
   - Metrics: "curr_arr", "prev_arr", "latest closed quarter ARR" (SKU mart), "subscription_indicator", "has_subscriptions"
   - Taxonomy: "offering_group", "offering_line", "offering_category", "quoting tier", "rh_offering_tier"
   - ⚠️ **DO NOT route corporate catalog-only questions here** — aliases, components, reference lifecycle without OLM metrics → **Official Product List**

   **Keywords that trigger Partner Programs (TJ staging, partner rewards processing):**
   - Transaction journal: "transaction journal", "TJ", "failed to create TJ", "error reason", "failed to process"
   - Partner activities: "open_mdm_id", "partner training", "PTP", "training activity", "claims failed", "loyalty_tj", "rebates_stage"
   - Credentials: "seller credential", "tech credential", "certification expiring", "partner credential"
   - Payments: "pay_to", "rebate paid to partner", "rebate disbursement"
   - Sell-with: "EVF", "sell-with", "sell with pipeline" (partner program / TJ context)
   - ⚠️ **DO NOT route points/tier here** — "points earned", "loyalty points", "partner tier", "next tier" → **SISALS**

   **Keywords that trigger MDMPRODUCT (`mdmproduct_db.harbor_marts`):**
   - SKU master: "MDM product", "MDMPRODUCT", "product master", "SKU", "SKU lookup", "SKU hierarchy", "parent SKU", "child SKU", "MDM_ID"
   - Pricing: "MSRP", "list price", "product pricing", "price by region", "active price", "pricing data" (master data, not discount analysis)
   - Quoting: "quoting tier", "quotable SKU", "CPQ eligible", "TIER_1", "TIER_2", "generally available SKU"
   - Product attributes: "offering program", "offering group", "offering category", "product category", "business unit" (in MDM product context), "`mdmproduct_db`", "`HARBOR_SKU_CURRENT`", "`HARBOR_PRICE_CURRENT`"
   - Lifecycle: "product created", "product modified", "product EOL date", "end of life SKU" (MDM-level, not official catalog)
   - Technical: "product architecture", "cores", "sockets", "subscription type", "service level" (MDM product context)
   - ⚠️ DO NOT route to MDMPRODUCT: "product catalog", "product portfolio", "product alias" (→ **Official Product List**); "discount %", "MSRP vs TCV" (→ **Discounting**)
   **Keywords that trigger MDMPARTY (`mdmparty_db.partylens_marts`):**
   - Party master: "MDM party", "MDMPARTY", "party master", "golden party", "mdm party id", "`mdm_party_id`"
   - Firmographics / D&B at party level: "party DUNS", "domestic ultimate", "global ultimate parent", "company type" (party context)
   - Geography: "party address", "customer address" (master data, not transactional ship-to on orders)
   - Identifiers: "party alternate id", "party identifier", "SFDC account id on party" (master side)
   - Mart objects: "`partylens_marts`", "`party_lens_dim_v1`", "`party_lens_*`", "`mdm_party_lens_*`", intercompany party relationships, party role customer/partner in MDM
   - D&B satellites **in `mdmparty_db.partylens_marts`** for party enrichment — not standalone DNB_DB market benchmarking (see **HG Insights** / **GTM** as appropriate)

   **Keywords that trigger Rosettastone (customer identifier mapping - EBS ↔ RHSC only):**
   - EBS ↔ RHSC ID: "EBS for RHSC ID", "RHSC ID for EBS", "EBS assigned/linked/tied/corresponds to RHSC"
   - EBS ↔ Sales Group: "EBS for Sales Group", "Sales Group for EBS", "EBS linked to Sales Group"
   - EBS ↔ Global Sales Group: "EBS for Global Sales Group", "Global Sales Group for EBS", "GSG for EBS"
   - Customer identifier: "customer identifier mapping", "account mapping", "EBS to RHSC translation"
   - ⚠️ DO NOT route to Rosettastone: Any query involving "MDM" (MDM for EBS, EBS for MDM, MDM to RHSC, etc.), "Bookings Data", "opportunity data", "legacy RHSC ID", or "Sales Group for RHSC ID" without EBS
   - ⚠️ MDM-to-EBS queries: "MDM ID for EBS", "EBS for MDM" → Route to **EBS** data product (`ebs_db`), NOT Rosettastone
   - ⚠️ Sales Group ↔ Global Sales Group queries (without EBS): "Which sales groups for [GSG]", "GSG for sales group" → Route to **SalesHierarchy** (`saleshierarchy_db`), NOT Rosettastone

   **Keywords that trigger SalesHierarchy (customer segmentation / sales hierarchy):**
   - Sales hierarchy: "sales hierarchy", "customer hierarchy", "account hierarchy", "hierarchy lookup"
   - GSG/SG: "global sales group", "GSG", "sales group", "SG assignment", "sales group code"
   - Segmentation: "customer segmentation", "segment assignment", "which segment", "account segment", "market segment", "subsegment"
   - Account flags: "global account", "telco account", "IBM account", "partner account", "HCS account", "Dragonfly", "SIA", "TNT30"
   - Territory mapping: "territory for account", "account territory", "territory assignment for [account]"
   - Planning hierarchy: "planning year hierarchy", "next year segmentation", "planning sales hierarchy"
   - MDM-to-SG/GSG: "MDM for Sales Group", "Sales Group for MDM", "MDM for Global Sales Group", "Global Sales Group for MDM"
   - SG ↔ GSG: "Sales Group for Global Sales Group", "Global Sales Group for Sales Group", "which sales groups in GSG"
   - ⚠️ DO NOT route to SalesHierarchy: "bookings", "ARR", "ACV", "revenue", "EBS to RHSC" (those go to Bookingsmaster, RevenueMaster, or Rosettastone respectively)

   **Keywords that trigger ExpenseMaster (corporate budgets / GL / IT forecast & TBM):**
