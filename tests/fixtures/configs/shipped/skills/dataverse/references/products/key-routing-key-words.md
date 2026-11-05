### Key Routing Key Words

* **Keywords to INCLUDE (The “Green Light”):**
  Subscription, entitlement, Red Hat, RHEL, OpenShift; EBS account, EBS account number, party, party name, party number, customer; contract, contract number, EBS contract; SKU, parent SKU, product, product description; subscription status, active, expired, terminated; start date, end date, term, subscription term; price, amount, net price, list price, quantity, qty, currency; INTELLIGENTACCESS\_DB, intelligent access, intelligentaccess

* **Keywords to EXCLUDE (The “Red Light”):** Specific terms or queries that should NEVER route to this data product.
  Opportunity (pipeline/deal), forecast, booking; support case, ticket, incident, service request; consumption, usage data, telemetry, metrics; invoice, payment, billing, AR, accounts receivable; partner (as primary topic), reseller, distributor, channel; campaign, lead, marketing, MQL; product catalog, product master, product hierarchy; price list, discount, pricing rules, MSRP; renewal quote, renewal opportunity, renewal forecast

**KEY DISTINCTION:**
   - **IntelligentAccess** = What customers **currently have or had** (entitlements, subscriptions, SKUs)
   - **Bookingsmaster** = What customers **bought** (ARR, ACV, pipeline, deals)
   - **Renewals** = What customers **might renew** (renewal forecasts, renewal pipeline)

## 📄 Unstructured Data Products

These data products store embedded documentation and knowledge bases as vector embeddings in Snowflake. They support semantic search for platform enablement — NOT business analytics. They contain no revenue, bookings, headcount, expense, or transactional data.

⚠️ **CRITICAL ROUTING RULE**: Unstructured data products answer "how do I" questions about the Dataverse **platform itself** (processes, tooling, governance). They do NOT answer questions about business data. If the user wants numbers, metrics, reports, or analysis — route to the appropriate business data product instead.

---
