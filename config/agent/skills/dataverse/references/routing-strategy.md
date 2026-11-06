### Query Routing Strategy

Step 2, telling sales *intent* apart (pipeline vs bookings vs revenue), is the one that decides most wrong answers — it is in `routing-sales-intent.md`.


1. **Identify the domain** - Determine which business area the query relates to:
   - **Pipeline queries** (open pipeline, pipeline for [product/geo], pipeline snapshots, pipeline YoY/MoM, pipeline conversion) → **Bookingsmaster** (default for pipeline queries)
   - **Forecast-specific analytics** (pipeline coverage ratios, pipeline velocity, waterfall movements, forecast vs actual) → **Forecasting**
   - **Average Selling Price (ASP)** (ASP by product, price per core/socket/node, entitlements, ASP trends, cohort retention) → **Forecasting** (`pge_marts`)
   - IT expense **forecasts**/IT budget planning/projected IT spend → **ExpenseMaster** (ITPF / TBM marts; see `aggregate/expensemaster/README.md`)
   - **Historical IT expenses/actual IT spend/past IT costs** → **ExpenseMaster** (GL / OneStream Actual)
   - **Corporate expenses/budgets/GL transactions** → **ExpenseMaster**
   - Project/issue tracking → **JIRA**
   - People/organization → **RoverPeople**
   - Sales compensation/commission payouts/incentive plans/territory credit → **SI Execution**
   - **Sales targets/target allocation/quarterly targets** → **Sales Planning** (QUARTERIZATION_MARTS)
   - **Seller quotas/quota assignments/quota coverage** → **Sales Planning** (QUOTA_MARTS)
   - **Red Hat internal IT spend / corporate vendor spend** (GL, actuals, ITPF/TBM, cost center, PO impact, "our AWS spend") → **ExpenseMaster**
   - **Prospecting, competitive intelligence, market intelligence on RHSC accounts** → **GTM** (not HG Insights alone)
   - **IT spend/budget comparison between companies, TAM, market-wide technographic data** → **HG Insights**
   - **RHSC account intelligence (product flags, intent, competitive footprint)** → **GTM**
   - **Red Hat bookings/ARR/ACV/sales performance** → **Bookingsmaster**
   - **Red Hat actual revenue/GL revenue/recognized revenue** → **RevenueMaster**
   - **Discount analysis/MSRP vs TCV comparison/high discount deals** → **Discounting**
   - 🔴 Legacy Salesforce system → **SFSalesLegacy** (ONLY when user explicitly requests legacy system)
   - **Enterprise data standards/reference data/SIC codes** → **SourceDataGovernance**
   - **Product catalog/product attributes/product portfolio/product types** (reference catalog) → **Official Product List**
   - **OLM/offering lifecycle/SKU leverage/inactivation candidates/curr_arr on olm_final_data** → **Offering Lifecycle Management (OLM)**
   - **MDM product / SKU master / SKU hierarchy / product pricing (MSRP) / `mdmproduct_db`** → **MDMPRODUCT** (`mdmproduct_db.harbor_marts`)
   - **MDM party / party master / party hierarchy / `mdm_party_id` / `mdmparty_db`** → **MDMPARTY** (`mdmparty_db.partylens_marts`; legacy `marts` decommissioned)
   - **Customer segmentation / sales hierarchy / GSG / SG / account flags** → **SalesHierarchy**

   **🔑 CRITICAL DISTINCTION #1: Revenue vs. Bookings**
   - ⚠️ **Query contains ANY form of "revenue"** (recognized, actual, GL, revenue reporting, revenue forecasting, revenue planning, service revenue, subscription revenue, revenue components) → **RevenueMaster** 💰
   - ⚠️ **NEVER route revenue questions to Bookingsmaster** - Bookingsmaster is for bookings/ARR/ACV only
   - Query contains **"bookings", "ARR", "ACV", "sales performance"** (but NOT revenue) → **Bookingsmaster** ⭐
   - **Example:** "Show me revenue for Q2" → **RevenueMaster** (NOT Bookingsmaster)
   - **Example:** "Show me recognized revenue" → **RevenueMaster** (NOT Bookingsmaster)
   - **Example:** "Show me bookings for Q2" → **Bookingsmaster**
   - **Example:** "Show me ARR for Q2" → **Bookingsmaster** (ARR is bookings metric, not revenue)

   **🔑 CRITICAL DISTINCTION #2: ExpenseMaster vs. GTM vs. HG Insights vs. Bookingsmaster**
   - **Red Hat internal spend** (GL, IT actuals, ITPF/TBM, corporate/AWS/Dell/Microsoft **vendor spend at RH**) → **ExpenseMaster** 💸
   - **RHSC account intelligence** (product flags, intent, competitive footprint, prospecting within known accounts) → **GTM** 📊
   - **IT spend/budget comparison between companies**, market technographic data, TAM → **HG Insights** 🎯
   - Red Hat **SALES**/purchases/bookings → **Bookingsmaster** ⭐

   **🔑 CRITICAL DISTINCTION #3: Internal Red Hat Spend vs. Third-Party IT Budgets**
   - ⚠️ **Red Hat's internal expenses/vendor spend** → **ExpenseMaster** 💸
     - "total spend of AWS", "vendor spend", "how much did we spend on X", "Red Hat's AWS spend"
     - "actual spend", "historical spend", "we spent", "our spend", "company spend"
     - Questions about Red Hat's internal costs, GL transactions, or vendor payments
     - **Examples:** "total spend of AWS in Dec 25", "how much did we spend on Azure last quarter", "vendor spend breakdown for 2025"
   - ⚠️ **Third-party company IT budgets (RHSC accounts for prospecting)** → **GTM** 📊
     - "[Company name]'s cloud spend", "[Account]'s IT budget", "Walmart's cloud spend"
     - IT budgets for prospecting, competitive analysis, and account intelligence
     - Questions about external companies' IT budgets (not Red Hat's internal spend)
     - **Examples:** "what is Walmart's cloud spend", "show accounts with high AWS spend", "companies with high virtualization budget"
   - ⚠️ **PRIORITY:** Check for internal spend keywords (ExpenseMaster) FIRST before routing to GTM

3. **Check for cross-domain needs** - If the query requires data from multiple domains, route to the appropriate aggregate data product:
   - Bookings + Sales + Subscriptions + Products + Customers → **Bookingsmaster**
   - Revenue + GL + Revenue Components + Geographic Revenue → **RevenueMaster**
   - **Organization hierarchy + People data** (e.g., "employees in IT org", "leader of Marketing", "who runs Marketing", "who leads Engineering") → **fammatrix FIRST** (get cost centers), **then RoverPeople** (get employee data)

4. **Handle out-of-scope queries** - If query doesn't match any data product's scope:
   - Return "No data products identified" rather than forcing to an incorrect product

---
