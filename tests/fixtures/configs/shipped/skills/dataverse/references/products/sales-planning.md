### **Sales Planning**
**Database:** `salesplanning_db`
**Schemas:** `QUARTERIZATION_MARTS`, `QUOTA_MARTS`
**Maturity:** AI Experimental

⚠️ **CRITICAL: Sales Planning is for SALES TARGETS (bookings/ARR targets) only. Revenue targets are not available. Revenue forecasts are in RevenueMaster.**

Sales Planning data product providing quarterization marts for sales target planning, quarterly target allocation, and actual vs. target performance tracking across geographic territories, product offerings, and sales channels. Also includes quota marts for individual seller quota assignments, territory coverage, and quota performance tracking.

Enables sales operations and finance teams to plan, allocate, and track quarterly sales targets (bookings/ARR targets) supporting the annual sales planning cycle and performance monitoring. The quota marts link quarterly targets to specific sales associates through seller profiles, sales roles, and territory assignments.

**Primary use cases:**
- **Quarterization Marts:** Quarterly target allocation, target vs. actual analysis, geographic target distribution, CCSP (Cloud Computing Service Provider) target tracking, and sales plan period management
- **Quota Marts:** Individual seller quota assignments, quota vs. target analysis, seller territory coverage, quota gap analysis, and quota stacking scenarios

**When to route here:**
- **Target Planning:** Queries about sales targets, quarterly targets, target allocation, target vs. actual comparison, planning targets, territory targets, or quarterization methods
- **Seller Quotas (Current Year):** Queries about **current fiscal year** individual seller quotas, quota assignments, quota by territory, quota by sales role, quota coverage, quota gap to minimum, or quota stacking
- **Restated Renewals:** Queries explicitly about restated renewals should route to **Sales Planning MARTS**

⚠️ **TEMPORAL ROUTING RULE FOR QUOTAS:**
- **Current fiscal year quota queries** → **Sales Planning** (QUOTA_MARTS)
- **Past fiscal year quota queries** (historical quota data) → **SI Execution**

**Data Scope & Coverage:**

*What IS in Sales Planning (Quarterization Marts):*
- Quarterly sales target allocations (Q1-Q4) for next fiscal year
- Current year actual amounts by quarter (ACTUAL_CY_Q1-Q4_AMT)
- Next year target amounts by quarter (TARGET_NY_Q1-Q4_AMT)
- Geographic hierarchy: Planning Geo → Region → Subregion → Pod → Territory
- Product hierarchy: Offering Group → Offering Line → Offering Category
- CCSP (Cloud Computing Service Provider) targets with monthly/yearly subcomponents
- Renewal subscription targets (SUBSCRIPTIONS component)
- Quarterization methods: TOPLINE (top-down) and BOOKINGS (historical pattern)
- Sales group and global sales group codes for territory mapping
- HCS (Hybrid Committed Spend) event type tracking
- Sales motion classification (Sell To)
- Planning period tracking (e.g., 2026-FY)

*What IS in Sales Planning (Quota Marts):*
- Individual seller quota assignments with quarterly breakdowns (QUOTA_Q1_AMT - QUOTA_Q4_AMT)
- Seller profile and sales role information (associate_employee_id, sales_role_id)
- Territory-based quota allocation with assignment percentages
- Quota vs. target comparisons (quota amounts vs. target_cy_q1_amt - target_cy_q4_amt)
- Seller territory coverage and assignments
- Quota gap to minimum analysis (GAP_TO_MINIMUM)
- Quota stacking scenarios (multiple sellers on same territory)
- Measurement target detail linking quotas to quarterly targets
- Sales role element breakdowns (element, element_desc, metric, weight)

*What IS NOT in Sales Planning:*
- **Revenue targets** → Not available
- **Revenue data** (revenue recognition, GL revenue, recognized revenue, revenue forecasts) → Use **RevenueMaster**
- **Past fiscal year quota data** (historical quotas) → Use **SI Execution**
- Sales compensation and incentive payouts → Use **SI Execution**
- Commission calculations or payout amounts → Use **SI Execution**
- Actual deal-level bookings or transactions → Use **Bookingsmaster**
- Revenue recognition data → Use **RevenueMaster**
- Customer or account-level information → Use **Bookingsmaster**
- Pipeline or opportunity data → Use **Bookingsmaster**

**🔑 KEY ROUTING RULES:**
- **"What are the sales targets for..."** → **Sales Planning** (sales target allocation data - bookings/ARR targets in QUARTERIZATION_MARTS)
- **"How did we perform vs. target..."** → **Sales Planning** (target vs. actual comparison for sales targets in QUARTERIZATION_MARTS)
- **"What is my quota this year..."** / **"Current year quota..."** / **"FY26 quota..."** → **Sales Planning** (current fiscal year quota in QUOTA_MARTS)
- **"What was my quota last year..."** / **"Historical quota..."** / **"FY25 quota..."** → **SI Execution** (past fiscal year quota data)
- **"Quota coverage..."** / **"Quota gap..."** / **"Quota stacking..."** → **Sales Planning** (current year quota analytics in QUOTA_MARTS)
- **"Show me actual bookings..."** → **Bookingsmaster** (transactional bookings data)
- **"Sales compensation..."** / **"Commission payouts..."** / **"Incentive plans..."** → **SI Execution** (compensation and commission data)
- **"What are the revenue targets..."** → Not available
- **"Show me revenue forecast..."** → **RevenueMaster** (revenue forecasts, NOT Sales Planning)

---
