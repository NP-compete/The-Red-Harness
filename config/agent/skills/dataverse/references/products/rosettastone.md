### **Rosettastone**
**Database:** `rosettastone_db`

⚠️ **CRITICAL: Rosettastone is for CUSTOMER IDENTIFIER MAPPING only (EBS ↔ RHSC). It does NOT contain bookings, opportunities, or transaction data. For sales/bookings data, use Bookingsmaster.**

**⚠️ SCHEMA & COLUMN EXCLUSIONS:**
- Do **NOT** use tables from `REPORTING_MARTS` schema. Only use `MARTS` schema tables.
- Do **NOT** use columns `match_type` or `match_rank` — use `match_source` instead.

Rosetta Stone is the definitive customer identifier mapping table that relates EBS account numbers to RHSC (Red Hat Sales Cloud) account IDs. It acts as a "translator" between different customer identifiers used across Red Hat's business systems.

The primary purpose is to enable data teams to accurately join and relate customer data across sales, customer support, customer usage, and other data sources that use different customer identifiers.

**Core Business Questions:**
1. Which RHSC ID (or Sales Group or Global Sales Group) corresponds to this specific EBS number?
2. Which EBS account numbers fall under this RHSC ID (or Sales Group or Global Sales Group)?
3. What is the Sales Group or Global Sales Group assignment for a given EBS account?

**Primary use cases:** Customer identifier mapping, EBS to RHSC translation, Sales Group lookups, Global Sales Group identification, and cross-system customer data integration.

**When to route here:** Queries about mapping EBS numbers to RHSC IDs, mapping RHSC IDs to EBS numbers, mapping EBS to Sales Groups, mapping EBS to Global Sales Groups, or any customer identifier translation between EBS and RHSC

**✅ ROUTE HERE (Keywords to INCLUDE):**
Queries involving mapping/relationship between EBS and RHSC identifiers using relationship verbs:
- **EBS ↔ RHSC ID patterns:** "EBS for RHSC ID", "EBS assigned/linked/tied/corresponds/affiliated/related to RHSC ID", "RHSC ID for EBS", "RHSC ID assigned/linked/tied/corresponds/affiliated/related to EBS"
- **EBS ↔ Sales Group patterns:** "EBS for Sales Group", "EBS assigned/linked/tied/corresponds/affiliated/related to Sales Group", "Sales Group for EBS", "Sales Group assigned/linked/tied/corresponds/affiliated/related to EBS"
- **EBS ↔ Global Sales Group patterns:** "EBS for Global Sales Group", "EBS assigned/linked/tied/corresponds/affiliated/related to Global Sales Group", "Global Sales Group for EBS", "Global Sales Group assigned/linked/tied/corresponds/affiliated/related to EBS"
- **EBS number/ID variants:** Same patterns with "EBS number" or "EBS ID" instead of "EBS"
- **RHSC number variants:** Same patterns with "RHSC number" instead of "RHSC ID"
- **Name variants:** "Sales Group name for EBS", "Global Sales Group name for EBS"
- **Customer identifier keywords:** "customer identifier mapping", "account mapping", "EBS to RHSC translation"

**❌ DO NOT ROUTE HERE (Keywords to EXCLUDE):**
Queries involving MDM (Master Data Management) or unrelated data types:
- **MDM ↔ EBS patterns:** "MDM for EBS", "MDM assigned/linked/tied/corresponds/affiliated/related to EBS", "EBS for MDM", "EBS assigned/linked/tied/corresponds/affiliated/related to MDM"
- **MDM ↔ RHSC ID patterns:** "MDM for RHSC ID", "MDM assigned/linked/tied/corresponds/affiliated/related to RHSC ID", "RHSC ID for MDM"
- **MDM ↔ Sales Group patterns:** "MDM for Sales Group", "Sales Group for MDM", "MDM assigned/linked/tied/corresponds to Sales Group"
- **MDM ↔ Global Sales Group patterns:** "MDM for Global Sales Group", "Global Sales Group for MDM"
- **Sales Group ↔ RHSC ID patterns (without EBS):** "Sales Group for RHSC ID", "RHSC ID for Sales Group", "Global Sales Group for RHSC ID", "RHSC ID for Global Sales Group"
- **MDM number/ID variants:** "MDM number for EBS", "MDM ID for EBS", "EBS number for MDM"
- **Bookings Data queries:** "Bookings Data for Customer ID", "Bookings Data assigned/linked/tied to Customer ID"
- **Transaction data:** Bookings, opportunities, revenue, customer transaction history → Use **Bookingsmaster** or **RevenueMaster**
- **Legacy RHSC IDs:** Discontinued identifiers not in current mapping

**⚠️ ROUTING FOR MDM-TO-EBS QUERIES:**
- **MDM ID for EBS number** → Route to **EBS** data product (`ebs_db`)
- **EBS number for MDM ID** → Route to **EBS** data product (`ebs_db`)
- Any query asking for MDM ID associated with EBS, or EBS associated with MDM → Route to **EBS**, NOT Rosettastone

**⚠️ ROUTING FOR MDM-TO-RHSC QUERIES:**
- **MDM ID for RHSC ID** → Route to **SFSales** data product (`sfsales_db`)
- **RHSC ID for MDM ID** → Route to **SFSales** data product (`sfsales_db`)
- "What is the MDM ID for RHSC ID X?" → Route to **SFSales**, NOT Rosettastone
- Any query asking for MDM ID associated with RHSC, or RHSC associated with MDM → Route to **SFSales**, NOT Rosettastone

**⚠️ ROUTING FOR MDM-TO-SALES GROUP/GLOBAL SALES GROUP QUERIES:**
- **MDM ID for Sales Group** → Route to **SalesHierarchy** data product (`saleshierarchy_db`)
- **MDM ID for Global Sales Group** → Route to **SalesHierarchy** data product (`saleshierarchy_db`)
- **Sales Group for MDM ID** → Route to **SalesHierarchy** data product (`saleshierarchy_db`)
- **Global Sales Group for MDM ID** → Route to **SalesHierarchy** data product (`saleshierarchy_db`)
- "What is the MDM ID for Sales Group X?" → Route to **SalesHierarchy**, NOT Rosettastone
- "What is the MDM ID for Global Sales Group X?" → Route to **SalesHierarchy**, NOT Rosettastone
- Any query asking for MDM ID associated with Sales Group or Global Sales Group → Route to **SalesHierarchy**, NOT Rosettastone

**⚠️ ROUTING FOR SALES GROUP ↔ GLOBAL SALES GROUP QUERIES (WITHOUT EBS):**
- **Sales Group for Global Sales Group** → Route to **SalesHierarchy** data product (`saleshierarchy_db`)
- **Global Sales Group for Sales Group** → Route to **SalesHierarchy** data product (`saleshierarchy_db`)
- "Which sales groups correspond to [Global Sales Group]?" → Route to **SalesHierarchy**, NOT Rosettastone
- "Which global sales group does [Sales Group] belong to?" → Route to **SalesHierarchy**, NOT Rosettastone
- Any query about Sales Group ↔ Global Sales Group relationships **without mentioning EBS** → Route to **SalesHierarchy**

**🔑 KEY RULE:** Rosettastone's primary identifier is **EBS number**. If the query does NOT involve EBS and is asking about Sales Group/Global Sales Group hierarchies, route to **SalesHierarchy** instead.

**❓ AMBIGUOUS QUERIES - ASK FOR CLARIFICATION:**

**1. Seller Information Queries:**
When a user asks for "seller details", "seller information", or similar vague queries for an EBS number, the intent is unclear:
- **Sales side seller information** (account owner, sales rep, territory assignment) → Route to **Rosettastone** (contains account owner info for each EBS-RHSC mapping)
- **EBS side seller information** (vendor/supplier data from Oracle EBS) → Route to **EBS** data product (`ebs_db`)

**Action Required:** If the query mentions "seller" or "seller details" for an EBS number without clear context, ASK THE USER TO CLARIFY:
> "Are you looking for:
> 1. **Sales account owner information** (who owns this account in Red Hat Sales Cloud) - I can help with that using Rosettastone
> 2. **EBS vendor/supplier information** (seller data from Oracle EBS system) - I can help with that using EBS data product
>
> Please specify which type of seller information you need."

**2. Unclear Identifier Queries:**
When a user asks for "customer IDs" or provides a numeric value without specifying the identifier type, the query is ambiguous:
- Examples: "Show me customer IDs for 127896", "What are the IDs for 127896", "Customer info for 127896", "Show me the ID for 127896"

**Action Required:** If the query contains vague terms like "customer ID" or an unspecified numeric value, ASK THE USER TO CLARIFY:
> "Your query is unclear. Please help me understand:
> 1. **What type of identifier is the value you provided?** (e.g., EBS number, RHSC ID, MDM ID, Sales Group ID)
> 2. **What type of customer ID are you looking for?** (e.g., EBS number, RHSC ID, MDM ID)
>
> For example:
> - 'What is the RHSC ID for EBS number 127896?' - I can help with that using Rosettastone
> - 'What is the MDM ID for EBS number 127896?' - I can help with that using EBS data product
>
> Please rephrase your question with specific identifier types."

**📖 BUSINESS TERMINOLOGY - COMMON ABBREVIATIONS:**
When users mention these terms, translate them to the correct field values:
- **NAPS** = North America Public Sector = "AMER public sector" = NA Public Sector
- **AMER** = Americas (North America + Latin America)
- **NA** = North America
- **EMEA** = Europe, Middle East, and Africa
- **APAC** = Asia Pacific
- **LATAM** = Latin America
- **Public Sector** = Government, Education, Healthcare segments

**Example Query Translations:**
- "I'm a seller in AMER public sector" → Filter by Geo = "NA" or "AMER" AND Segment = "Public Sector" (or Coverage Segment containing "NAPS")
- "Show me NAPS accounts" → Filter by Coverage Segment or Account Segment containing "NAPS" or "Public Sector" in NA region

**Data Scope & Coverage:**

*What IS in Rosettastone:*
- Definitive 1:1 mapping of EBS account numbers to RHSC account IDs
- MDM party ID associations for each mapping
- Sales Group (SG) and Global Sales Group (GSG) identifiers and names for each mapping
- RHSC account name and segment information for each mapping
- Geographic hierarchy (Geo, Region, Subregion, Pod, Territory) for each mapping
- Account segment and coverage segment classifications for each mapping
- Match source indicator (RosettaStone = traditional mapping, Enhanced = enhanced mapping logic)
- Account owner information (ID and name) for each mapping
- Industry and country information for each mapping

*What IS NOT in Rosettastone:*
- EBS accounts with multiple RHSC IDs or multiple MDM IDs (filtered out)
- EBS accounts with missing MDM ID or RHSC ID (excluded)
- Legacy RHSC identifiers (discontinued)
- Bookings or opportunity data → Use **Bookingsmaster**
- Revenue data → Use **RevenueMaster**
- Customer transaction history → Use **Bookingsmaster**
- Seller compensation data → Use **SI Execution**
- Current year quota data → Use **Sales Planning** (QUOTA_MARTS)
- Past year quota data → Use **SI Execution**

**🔑 KEY MAPPING RULES:**
- Each EBS account number maps to exactly ONE RHSC account ID
- Multiple EBS account numbers CAN roll up to the same RHSC account ID
- Multiple EBS account numbers CAN roll up to the same MDM party ID
- MDM party ID is the backend identifier linking mappings across systems

**Data Sources:**
Rosettastone integrates data from the following source-aligned data products:
- **mdmparty_db.partylens_marts** - Master Data Management party identifiers
- **sfsales_db** - Red Hat Sales Cloud (Salesforce) account data
- **ebs_db** - Oracle Enterprise Business Suite account numbers

**Error Reporting:** If you believe there is an error in the Rosetta Stone mapping, submit an error form in ServiceNow at: https://redhat.service-now.com/help?id=sc_cat_item&sys_id=52e9131887d076503439a8683cbb35e3

---
