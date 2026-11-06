### **Forecasting**
**Database:** `forecasting_db`
**Schemas:** `marts`, `pge_marts`
**Maturity:** AI Experimental

Forecasting provides comprehensive **sales pipeline analytics and forecasting** along with **Average Selling Price (ASP) analytics** across Red Hat's product portfolio. The `marts` schema covers pipeline management, forecast categories, MJ tags, waterfall movements, historical bookings, pipeline snapshots, and bookings/quota targets. The `pge_marts` schema provides standardized ASP calculations for RHEL, Ansible, OpenShift, and Application Services, plus product cohort retention analysis.

**Primary use cases:** Pipeline coverage analysis, forecast vs actual comparison, waterfall movement analysis, pipeline velocity scoring, MJ/Upside tag tracking, Average Selling Price (ASP) by product/geo/segment/channel, entitlement-based unit economics, customer cohort retention and ARR analysis, ASP trend analysis.

**When to route here:** Queries about pipeline coverage ratios, pipeline velocity, waterfall movements, forecast vs actual, MJ overrides, statistical forecasts, Average Selling Price (ASP), price per unit/core/socket/node, entitlements, entitled units, channel adjustments, transfer price, product cohort analysis, customer retention ARR, ASP by product (RHEL/OpenShift/Ansible/App Services), ASP trends, ELS/EUS pricing impact.

**✅ ROUTE HERE when query contains:**
- "pipeline coverage", "pipeline velocity", "waterfall movement", "forecast vs actual"
- "MJ", "manager judgment", "upside tag", "forecast tag"
- "statistical forecast", "fivecast", "ML forecast"
- "ASP", "average selling price", "average sales price", "price per unit"
- "price per core", "price per socket", "price per node"
- "entitlement", "entitled units", "unit count"
- "channel adjustment", "transfer price", "distributor margin"
- "product cohort", "cohort analysis", "customer retention ARR"
- "RHEL ASP", "OpenShift ASP", "Ansible ASP", "App Services ASP"
- "ELS/EUS", "ELA exclusion", "bare metal ASP"

**❌ DO NOT route here for:**
- **General bookings / ARR / ACV without forecast or ASP context** → Use **Bookingsmaster**
- **Recognized/actual/GL revenue** → Use **RevenueMaster**
- **Discount analysis (MSRP vs TCV/ACV)** → Use **Discounting**
- **Sales targets / quota assignments** → Use **Sales Planning**
- **Renewal pipeline** → Use **Renewals**
- **SKU master data / product hierarchy** → Use **MDMPRODUCT**
- **OLM offering lifecycle / SKU leverage** → Use **OLM** (though pge_marts sources entitlement data from OLM)

**Data Scope & Coverage:**

*What IS in Forecasting (marts):*
- Current pipeline via `forecasting_comprehensive_pipeline` (NRT near-real-time)
- Historical bookings via `abv_global_historical_bookings_lite_crma`
- Pipeline snapshots via `abv_global_pipeline_snapshot_lite_crma`
- MJ and Upside forecast tags via `blt_opportunity_forecast_tag` (audit trail)
- Waterfall movements via `waterfall_movement_acv`
- Pipeline trends via `pipeline_trends_acv`
- Bookings/quota/ARR targets from Anaplan via `core_global_target`
- ML/statistical forecasts via `abv_crma_fivecast_forecast_daily`

*What IS in Forecasting (pge_marts):*
- Average Selling Price (ASP) entitlements across RHEL, Ansible, OpenShift, and Application Services via `asp_entitlements`
- Aggregated ASP summary at product-level grain via `asp_summary`
- Product cohort retention analysis (ANSIBLE, OPENSHIFT, RHEL) via `product_cohort_analysis`
- Channel adjustments (Distributor, CCSP margins), entitlement quantities from OLM, exclusion flags
- Customer percentile buckets, ELS/EUS flags, bare metal flags, ELA flags

*What IS NOT in Forecasting:*
- General bookings / ARR / ACV / sales performance without forecast or ASP context → Use **Bookingsmaster**
- Actual revenue / recognized revenue / GL revenue → Use **RevenueMaster**
- Revenue targets or revenue planning → Use **RevenueMaster**
- Discount analysis (MSRP vs TCV comparison) → Use **Discounting**
- Sales quotas / compensation → Use **Sales Planning** or **SI Execution**
- Renewal-specific analytics → Use **Renewals**

**Data Sources:**
Forecasting integrates data from:
- **bookingsmaster_db** — Pipeline transactions, historical bookings, account and product data
- **sfsales_db** — Salesforce opportunity and account data
- **targets_db** — Anaplan bookings/quota targets
- **ard_db** — ARD forecasting signals
- **offeringlifecyclemgmt_db** — OLM entitlement quantities and count types for ASP calculations
- **enterpriseshared_db** — Bundle product splits, date dimensions, currency rates

---
