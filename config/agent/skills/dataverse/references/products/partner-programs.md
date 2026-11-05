### **Partner Programs**
**Database:** `partnerprograms_db`

Partner Programs is the **aggregate** data product for partner rewards and incentive processing in RHSC. It consolidates bookings, rebates, trainings, certifications, E2Open claims, and sell-with activities from multiple source systems into **transaction journal (TJ) staging** and error diagnostics used to operationalize partner rewards via Workato.

**Primary use cases:** Diagnose why an activity did not create a transaction journal; count trainings and list activity types by partner; track failed claims; analyze active or expiring credentials; rebate pay-to disbursements; sell-with EVF and partner booking ACV snapshots.

**When to route here:** Queries about **transaction journal**, **TJ failure**, **error reason**, **failed to process**, **open_mdm_id**, **partner training**, **PTP**, **claims** (TJ context), **loyalty staging**, **rebate staging**, **credentials**, **certifications expiring**, **pay_to**, **rebate paid to partner**, **EVF**, or **sell-with** in the partner programs context.

**❌ DO NOT route here for:**
- **Loyalty points balances, points earned, tier, tier progression, next tier** → Use **SISALS** (RHSC loyalty module)
- **Deal registration pipeline analytics** (rejected deals, CFQ+3, registration success rates) → Use **Forecasting**
- **General bookings / ACV+ without partner-program or TJ context** → Use **Bookingsmaster**
- **Recognized revenue / GL revenue** → Use **RevenueMaster**
- **Sales quotas and compensation** → Use **SI Execution** / **Sales Planning**

**Data Scope & Coverage:**

*What IS in Partner Programs:*
- Transaction journal staging and error diagnostics for loyalty, rebates, claims, training (PTP), and certifications
- Partner training and credential status (active and expiring)
- Rebate pay-to disbursement records
- Sell-with / EVF pipeline and partner booking ACV snapshots
- Partner account normalization and opportunity–partner attribution bridges
- Third-party-sourced claims (E2OPEN) and trainings (Seertech)

*What IS NOT in Partner Programs:*
- Published loyalty points balances, tier status, or redemption catalogs → **SISALS**
- Enterprise deal registration reporting and rejection analytics → **Forecasting**
- Bookings-scale opportunity metrics without partner-program context → **Bookingsmaster**

**Data Sources:**
Partner Programs integrates data from:
- **learningsources_db** — Partner Training Program (PTP) achievements
- **mdfe2open_db** — E2Open claims
- **sfsales_db** (rebates marts) — RHSC accounts, transaction journals, EVF
- **bookingsmaster_db** — Partner account mapping and transaction partner attribution
- **partnerprograms_db** — Staging and mart views for TJ processing

---
