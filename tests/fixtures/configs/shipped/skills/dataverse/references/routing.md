# LLM Foundry Data Products - Route Guidance

This guide helps route queries to the correct data product and database. Understanding the type and purpose of each data product is essential for accurate query routing.

---

## 📚 Understanding Data Products

### What is a Data Product?

Data products are built like software products. They are a reusable set of data assets and code that deliver a trusted dataset for a specific purpose. Each data product collects and processes data from relevant sources, ensures governance and compliance, and makes it accessible to anyone who needs it.

### How Data Products Become Databases

In the Dataverse ecosystem, each data product is deployed as a **Snowflake database** with a standardized naming convention: `<data_product_name>_db`. For example:
- The `bookingsmaster` data product becomes the `bookingsmaster_db` database
- The **`expensemaster`** data product becomes the **`expensemaster_db`** database (corporate expenses, GL, OneStream, IT planning / TBM via ITPF, and Cloudability(cloud spend actuals) — see **ExpenseMaster** below and `aggregate/expensemaster/README.md` for mart choice)

Within each database, data is organized into schemas (e.g., `marts`, `staging`, `intermediate`) that contain tables and views for analysis.

### Types of Data Products

There are three types of data products in Dataverse:

#### **Source-Aligned Data Products**

Source-aligned data products extract data directly from original operational systems with minimal transformation. They serve as the foundational entry point for data into the ecosystem.

**Key Characteristics:**
- **Direct extraction** from original sources (databases, APIs, transactional systems)
- **Minimal transformation** - focuses on basic cleansing and normalization
- **High granularity** - contains detailed, transaction-level data
- **Schema mirrors source systems** - preserves original structure and relationships
- **Foundation layer** - serves as input for aggregate data products

#### **Aggregate Data Products**

Aggregate data products combine and transform data from multiple source-aligned data products to provide unified, cross-domain insights and analytics.

**Key Characteristics:**
- **Data integration** - combines data from multiple source-aligned products
- **Data aggregation** - performs summing, averaging, grouping operations
- **Derived metrics and KPIs** - generates business metrics from integrated data
- **Cross-domain insights** - spans multiple business areas for comprehensive views
- **Summarization** - reduces detailed records to highlight trends and patterns
 #### **Unstructured Data Products**

Unstructured data products store embedded documentation, knowledge bases, and other non-tabular content as vector embeddings in Snowflake. They support semantic similarity search and keyword lookup — not traditional SQL analytics.

**Key Characteristics:**
- **Documentation and knowledge bases** - contains chunked text with vector embeddings
- **Semantic search** - uses VECTOR_COSINE_SIMILARITY for relevance ranking
- **No business metrics** - no revenue, bookings, headcount, or transactional data
- **Platform enablement** - answers "how do I" questions about Dataverse processes and tooling
- **Single-table architecture** - typically one CHUNKS_WITH_EMBEDDINGS table per product
---

## 📊 Source-Aligned Data Products

These data products extract data directly from operational systems and serve as foundational data sources.

---

## 🎯 Quick Reference - When to Use Each Product

| Query Topic | Route To | Database |
|-------------|----------|----------|
| **Forecast-specific analytics** (pipeline coverage ratios, velocity, waterfall movements) | **Forecasting** | `forecasting_db` |
| **Average Selling Price (ASP)** by product, geo, segment, channel | **Forecasting** 📊 | `forecasting_db` (`pge_marts`) |
| **Product cohort retention** (RHEL, OpenShift, Ansible ARR cohorts) | **Forecasting** 📊 | `forecasting_db` (`pge_marts`) |
| **AI agent performance, LLM costs, Langfuse traces, agent latency** | **AgentHealth** | `agenthealth_db` |
| **IT expense forecasts, IT budget planning, projected IT spend, ITPF / TBM** | **ExpenseMaster** 💸 | `expensemaster_db` (ITPF/TBM marts — see `aggregate/expensemaster/README.md`) |
| **Adobe Analytics, web analytics, marketing touchpoints, campaign attribution** | **Adobe** | `adobe_db` |
| **Historical IT expenses, actual IT spend, past IT costs** | **ExpenseMaster** 💸 | `expensemaster_db` |
| **Corporate expenses, budgets, expense planning, P&L** | **ExpenseMaster** 💸 | `expensemaster_db` |
| **GL transactions, sub-ledger, journal entries** | **ExpenseMaster** 💸 | `expensemaster_db` |
| **Budget vs actual, variance analysis** | **ExpenseMaster** 💸 | `expensemaster_db` |
| **Vendor spend (general or IT, historical)** | **ExpenseMaster** 💸 | `expensemaster_db` |
| **Hyperscaler cloud spend (past actuals), cloud accounts** | **ExpenseMaster** 💸 | `expensemaster_db` |
| Project management, issues, sprints | JIRA | `jira_db` |
| Sales compensation, commission payouts, incentive plans, territory credit mapping | SI Execution | `siexecution_db` |
| **Sales targets, quarterly targets, target allocation, target vs actual** | **Sales Planning** 🎯 | `salesplanning_db` (QUARTERIZATION_MARTS) |
| **Restated renewals** | **Sales Planning** 🎯 | `salesplanning_db` (MARTS) |
| **Seller quotas, quota assignments, quota by territory, quota coverage, quota gap** | **Sales Planning** 🎯 | `salesplanning_db` (QUOTA_MARTS) |
| **Employees, managers, org chart, team composition** | **RoverPeople** 👥 | `roverpeople_db` |
| **Employee distribution: "[person]'s TEAM by cost center"** | **RoverPeople** 👥 | `roverpeople_db` |
| **"How many employees work in cost center 857?"** | **RoverPeople** 👥 | `roverpeople_db` |
| **Cost center financial ownership, finance managers, FAM (Finance Account Manger Matrix)** | **fammatrix** 💼 | `fammatrix_db` |
| **Financial accountability: "[person] FINANCIALLY manages which cost centers"** | **fammatrix** 💼 | `fammatrix_db` |
| **"Who is the finance manager for cc871?"** | **fammatrix** 💼 | `fammatrix_db` |
| **"How many cost centers in Services organization?"** | **fammatrix** 💼 | `fammatrix_db` |
| **"List of departments under Marketing"** | **fammatrix** 💼 | `fammatrix_db` |
| **🔗 "How many associates work in the IT organization?"** | **fammatrix → RoverPeople** 🔗 | `fammatrix_db` → `roverpeople_db` |
| **🔗 "Who is the leader of the IT organization?"** | **fammatrix → RoverPeople** 🔗 | `fammatrix_db` → `roverpeople_db` |
| **🔗 "Who runs Marketing?" / "Who leads Marketing?"** | **fammatrix → RoverPeople** 🔗 | `fammatrix_db` → `roverpeople_db` |
| **🔗 Organization-level people queries (headcount/employees in a department)** | **fammatrix → RoverPeople** 🔗 | `fammatrix_db` → `roverpeople_db` |
| **Account intelligence: product flags, intent, competitive footprint, revenue potential (RHSC accounts)** | **GTM** 📊 | `gtm_db` |
| **RHEL/OpenShift/Ansible customer flags, product adoption flags** | **GTM** 📊 | `gtm_db` |
| **Buyer intent signals, accounts researching [product]** | **GTM** 📊 | `gtm_db` |
| **Revenue potential, incremental expansion potential by account** | **GTM** 📊 | `gtm_db` |
| **Cross-sell/upsell targeting, prospecting within RHSC account universe** | **GTM** 📊 | `gtm_db` |
| **Competitive displacement analysis (RHEL, OpenShift, Ansible competitors)** | **GTM** 📊 | `gtm_db` |
| **Territory/Pod/GEO account segmentation with product intelligence** | **GTM** 📊 | `gtm_db` |
| **Renewal pipeline, renewal ACV, renewal close rates, upcoming renewals** | **Renewals** ♻️ | `renewals_db` |
| **New vs renewal (NVR) metrics, renewal-stage forecasting** | **Renewals** ♻️ | `renewals_db` |
| **Red Hat internal AWS/Azure/vendor spend, IT actuals, GL, cost center, ITPF/TBM forecast** | **ExpenseMaster** 💸 | `expensemaster_db` |
| **IT spend/budget comparison between companies** | **HG Insights** 🎯 | `hginsights_db` |
| **TAM analysis, market penetration, product adoption trends** | **HG Insights** 🎯 | `hginsights_db` |
| **Companies using [any product] - market technographic data (not one RHSC account)** | **HG Insights** 🎯 | `hginsights_db` |
| **Competitive / technographic footprint for a specific RHSC account or territory** | **GTM** 📊 | `gtm_db` |
| **🔴 DISCOUNT ANALYSIS - "discount % for RHEL", "MSRP vs TCV", "high discount deals"** | **Discounting** 💲 | `discounting_db` |
| **Discount trends, discount percentage, discount validation** | **Discounting** 💲 | `discounting_db` |
| **MSRP comparison, list price vs actual price** | **Discounting** 💲 | `discounting_db` |
| **🔴 REVENUE queries - "revenue for Q2", "recognized revenue", "GL revenue"** | **RevenueMaster** 💰 | `revenuemaster_db` |
| **Revenue by geography, service/subscription revenue** | **RevenueMaster** 💰 | `revenuemaster_db` |
| **Revenue reporting** | **RevenueMaster** 💰 | `revenuemaster_db` |
| **🔴 BOOKINGS queries - "bookings for Q2", "ARR", "ACV"** | **Bookingsmaster** ⭐ | `bookingsmaster_db` |
| **Red Hat sales performance, opportunities, pipeline** | **Bookingsmaster** ⭐ | `bookingsmaster_db` |
| **Red Hat customer purchases and deal history** | **Bookingsmaster** ⭐ | `bookingsmaster_db` |
| 🔴 **Legacy Salesforce system ONLY** (requires explicit "legacy" keyword - frozen/stale data) | SFSalesLegacy | `sfsaleslegacy_db` |
| **Enterprise data standards, EDS codes, SIC codes, industry hierarchy** | **Source Data Governance** 📋 | `srcdatagovernance_db` |
| **Product catalog, product attributes, product portfolio, product types (reference catalog)** | **Official Product List** 📦 | `officialproductlist_db` |
| **OLM, offering lifecycle, SKU leverage/inactivation, curr_arr/prev_arr on olm_final_data, offering_group analytics** | **Offering Lifecycle Management (OLM)** 📦 | `offeringlifecyclemgmt_db` |
| **Transaction journal failures, partner training/claims/rebates staging, TJ error reason, pay_to rebates** | **Partner Programs** 🤝 | `partnerprograms_db` |
| **Partner credentials/certifications expiring, PTP activities by MDM ID, sell-with EVF staging** | **Partner Programs** 🤝 | `partnerprograms_db` |
| **Partner loyalty points balance, tier, tier progression, points earned** | **SISALS** (not Partner Programs) | RHSC loyalty module |
| **MDM product master, SKU hierarchy, MSRP, product pricing, quoting tiers** | **MDMPRODUCT** 📦 | `mdmproduct_db` (`harbor_marts`) |
| **MDM party master, hierarchy, identifiers, addresses (`partylens_marts`)** | **MDMPARTY** 🧩 | `mdmparty_db` (`partylens_marts`) |
| **Map EBS to RHSC ID, EBS to Sales Group, customer identifier mapping** | **Rosettastone** 🔗 | `rosettastone_db` |
| **EBS account to RHSC account translation** | **Rosettastone** 🔗 | `rosettastone_db` |
| **Customer segmentation, segment assignments, subsegments** | **SalesHierarchy** 🏢 | `saleshierarchy_db` |
| **Sales hierarchy: GSG → SG → MDM Party** | **SalesHierarchy** 🏢 | `saleshierarchy_db` |
| **Global Sales Group (GSG) lookups, Sales Group (SG) assignments** | **SalesHierarchy** 🏢 | `saleshierarchy_db` |
| **Account flags (global, telco, IBM, partner, HCS, Dragonfly)** | **SalesHierarchy** 🏢 | `saleshierarchy_db` |
| **Sales Group ↔ Global Sales Group relationships (without EBS)** | **SalesHierarchy** 🏢 | `saleshierarchy_db` |
| **MDM party to Sales Group / Global Sales Group mapping** | **SalesHierarchy** 🏢 | `saleshierarchy_db` |
| **Planning year hierarchy and segmentation changes** | **SalesHierarchy** 🏢 | `saleshierarchy_db` |
| **"How do I" Dataverse platform questions** (request access, build data products, set up dbt/Fivetran/Snowflake) | **DataverseHelp** 📄 | `dataversehelp_db` |
| **AI tool development guides** (build MCP server, deploy agent, Langfuse, OpenShift production path) | **DataverseHelp** 📄 | `dataversehelp_db` |
| **Dataverse governance policies, glossary, community resources, naming conventions** | **DataverseHelp** 📄 | `dataversehelp_db` |
