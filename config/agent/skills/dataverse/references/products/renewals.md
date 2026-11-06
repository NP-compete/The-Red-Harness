### **Renewals**
**Database:** `renewals_db`
**Schema:** `marts`

Renewals is the aggregate data product for subscription renewal pipeline analytics, renewal forecasting, and close-performance tracking. It consolidates renewal opportunities into a business-ready model for quarter-by-quarter planning and renewal execution.

**Primary use cases:** Renewal pipeline analysis, closed-renewal tracking, renewal ACV forecasting, renewal risk and stage analysis, and renewal performance by product/geo/account.

**When to route here:** Queries about renewal pipeline, renewal ACV, renewal close rates, renewal opportunity stages, renewal forecasting, or New-vs-Renewal (NVR) style renewal analysis.

**✅ ROUTE HERE when query contains:**
- "renewals", "renewal pipeline", "renewal ACV", "renewal close rate"
- "planning renewal", "renewal forecast", "renewal stage"
- "new vs renewal", "NVR", "upcoming renewals", "renewal risk"

**❌ DO NOT route here for:**
- **Recognized/actual/GL revenue** → Use **RevenueMaster**
- **General bookings-only analysis** without renewal scope → Use **Bookingsmaster**
- **Discount analysis** (MSRP vs TCV/ACV discount %) → Use **Discounting**
- **Restated renewals** → Use **Sales Planning** (`salesplanning_db.MARTS`)

**Data Scope & Coverage:**

*What IS in Renewals:*
- Renewal opportunity pipeline and closed-won outcomes in `CORE_GLOBAL_RENEWAL_POTENTIAL`
- Renewal-focused reporting flags: `reporting_renewals_flag`, `reporting_bookings_flag`, `planning_renewal_flag`
- ACV/TCV renewal financial fields (`acv_amount_usd_cy_pr`, `tcv_amount_usd_cy_pr`)
- Renewal stage and timing analytics (including fiscal quarter field `opportunity_close_date_fiscal_year_quarter_q`)
- HCS mapping support via `BLT_ACCOUNT_SALES_GROUP_MAPPING_HCS_EVENT_TYPE`
- Product enrichment support via `SKU_CURRENT`
- Historical end-of-day snapshot model in dbt: `core_global_renewal_potential_history`

*What IS NOT in Renewals:*
- Recognized revenue accounting or GL-reported revenue
- Generic non-renewal bookings reporting across all transaction types
- Sales quotas/targets or compensation plans

---
