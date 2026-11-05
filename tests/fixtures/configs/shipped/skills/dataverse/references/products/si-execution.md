### **SI Execution**
**Database:** `siexecution_db`
**Maturity:** AI Experimental

Sales Incentives (SI) Execution data product integrating Varicent and Anaplan systems for comprehensive sales compensation, quota management, and territory credit mapping analytics.

Manages sales compensation plans, territory assignments, quota allocations, and commission calculations across Red Hat's global sales organization.

**Primary use cases:** Sales compensation management, territory credit mapping, quota planning and attainment analysis, incentive strategy optimization, and sales operations analytics.

**When to route here:** Queries about sales compensation, **past fiscal year quotas** (historical quota data), territory assignments, credit allocation, sales incentive plans, manager approvals, payee performance, or sales operations planning. **For current fiscal year quotas, use Sales Planning.**

**Data Scope & Coverage:**

*What IS in SI Execution:*
- Territory credit mapping data from Anaplan and IAR Hub systems
- Quota planning and approval workflows with manager sign-off tracking
- **Historical/past fiscal year quota data** (for current year quotas, use **Sales Planning**)
- Payee (sales representative) information and assignments
- Compensation plan structures and components
- Geographic territory hierarchy (Geo → Region → Subregion → Territory)
- Sales group and coverage segment assignments
- Partner and channel credit allocation
- Product and offering category mapping to territories
- Quarter-based planning cycles and historical tracking
- Credit types (direct, indirect, split) and involvement levels (PRIMARY, SECONDARY)
- Manager approval workflows and change tracking
- Multi-currency quota management
- Rep type classifications (IQC, SA, SSA, Customer Success, Ecosystem)
- Compensation component analysis and attainment factors

*What IS NOT in SI Execution:*
- Actual sales performance or attainment results → Use **Bookingsmaster**
- Commission payout amounts or payment processing
- Revenue → Use **RevenueMaster**
- Bookings → Use **Bookingsmaster**
- Employee HR data beyond compensation context → Use **RoverPeople**

---
