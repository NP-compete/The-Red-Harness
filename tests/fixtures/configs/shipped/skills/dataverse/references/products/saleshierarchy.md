### **SalesHierarchy**
**Database:** `saleshierarchy_db`
**Schema:** `MARTS`
**Maturity:** AI Ready

Sales Hierarchy data product providing the authoritative client/customer hierarchy and segmentation that reflects Red Hat's Go-to-Market motions. Global Sales Group (GSG) is the highest-level account grouping for a given customer globally, used for discounting, HCS deals, and analytics. Sales Group (SG) is the first-level grouping for a given customer at the country level, used for planning (segments, coverage, and quotas).

Maintains current-year and planning-year hierarchy assignments including geographic territories, market segments, account flags, IBM designations, and partner classifications for ~150K MDM party records.

**Primary use cases:** Customer segmentation, sales hierarchy lookups, Global Sales Group (GSG) identification, Sales Group (SG) assignments, territory-to-account mapping, account flag analysis (global accounts, telco, IBM, partner, HCS), and planning-year hierarchy comparisons.

**When to route here:** Queries about customer segmentation, sales hierarchy, Global Sales Group (GSG), Sales Group (SG), segment assignments, territory assignments for accounts, account flags (global, telco, IBM, partner, HCS, Dragonfly, SIA, TNT30), Sales Group ↔ Global Sales Group relationships, MDM party hierarchy within the sales structure, or planning-year hierarchy changes.

**⚠️ CRITICAL ROUTING RULES:**
- **Sales hierarchy / segmentation / GSG / SG lookups** → Route to **SalesHierarchy**
- **MDM-to-Sales Group / Global Sales Group mappings** → Route to **SalesHierarchy** (NOT Rosettastone)
- **Sales Group ↔ Global Sales Group relationships (without EBS)** → Route to **SalesHierarchy** (NOT Rosettastone)
- **EBS-to-RHSC / EBS-to-Sales Group mappings** → Route to **Rosettastone** (NOT SalesHierarchy)
- **Actual bookings / ARR / ACV** → Route to **Bookingsmaster** (NOT SalesHierarchy)

**Data Scope & Coverage:**

*What IS in SalesHierarchy:*
- Sales hierarchy: Global Sales Group → Sales Group → MDM_PARTY_ID
- Current year customer hierarchy and segmentation (`GTM_SALES_HIERARCHY_MDM_DETAIL`)
- Planning year customer hierarchy and segmentation (`GTM_PLANNING_SALES_HIERARCHY_MDM_DETAIL`)
- Geo hierarchy: Geo → Region → Subregion
- Territory hierarchy: Territory Geo → Territory Region → Territory Subregion → Territory Pod → Territory Name
- Segment hierarchy: Segment → Subsegment (Commercial, Enterprise, Partner, TME, Unallocated)
- Account flags: IS_GLOBAL_ACCT, IS_TELCO_ACCT, IS_MANAGED_PARTER_ACCT, IS_UNALLOCATED, IS_PARTNER, IS_ACCT_PLANNING
- Program designation: IS_DRAGONFLY, IS_SIA, IS_TNT30, IS_HCS, IS_HCS_ALL
- IBM flags: IS_IBM_ENTERPRISE, IS_IBM_NATIONAL, IS_IBM_STRATEGIC, IS_IBMACCT, IS_IBM_PARTNER, IS_IBM_HORIZON, IS_IBM_STG_GLOBAL, IBM_MARKET
- Sales motion: IS_SELL_WITH, IS_SELL_THROUGH
- Partner type and industry vertical classifications
- RHSC account ID and name for each MDM party

*What IS NOT in SalesHierarchy:*
- **Actual bookings / ARR / ACV / TCV** → Use **Bookingsmaster**
- **Revenue recognition data** → Use **RevenueMaster**
- **Customer master data (party profile, addresses, D&B enrichment)** → Use **MDMPARTY** (`partylens_marts`)
- **Historical bookings or transaction data** → Use **Bookingsmaster**
- **Sales planning, targets, and quotas** → Use **Sales Planning**
- **EBS-to-RHSC account mapping** → Use **Rosettastone**

**🔑 KEY ROUTING RULES:**
- **"Which segment is [account] in?"** / **"Customer segmentation for..."** → **SalesHierarchy**
- **"What is the GSG for [account]?"** / **"Global Sales Group for..."** → **SalesHierarchy**
- **"What is the Sales Group for MDM ID X?"** / **"MDM ID for Sales Group X?"** → **SalesHierarchy**
- **"Which Sales Groups belong to Global Sales Group X?"** / **"GSG for Sales Group X?"** → **SalesHierarchy**
- **"Is [account] a global account / telco / IBM / partner?"** → **SalesHierarchy**
- **"Show accounts in Enterprise segment for EMEA"** → **SalesHierarchy**
- **"Territory assignments for [account]"** → **SalesHierarchy**
- **"Planning year hierarchy changes"** / **"Next year segmentation"** → **SalesHierarchy** (`GTM_PLANNING_SALES_HIERARCHY_MDM_DETAIL`)
- **"Show bookings for [account]"** → **Bookingsmaster** (NOT SalesHierarchy)
- **"Map EBS to RHSC ID"** → **Rosettastone** (NOT SalesHierarchy)

**Join Rules:**
- To **Bookingsmaster**: Join on `MDM_PARTY_ID` or `RHSC_ACCT_ID`
- To **MDM Product**: Join on `MDM_PARTY_ID`

**Data Sources:**
SalesHierarchy integrates data from the following source-aligned data products:
- **bookingsmaster_db** - Bookings and sales group data
- **mdmparty_db.partylens_marts** - MDM party identity and hierarchy

---
