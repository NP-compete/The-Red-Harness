### **ExpenseMaster**
**Database:** `expensemaster_db`

⚠️ **CRITICAL: ExpenseMaster is a COMPOSITE ANALYTICS DOMAIN spanning multiple expense and IT-financial sources in one database, NOT a single monolithic schema.**

ExpenseMaster provides comprehensive **expense and IT financial analytics** across Red Hat's operations by unifying:

1. **OneStream (Financial Planning & Budgeting)** — Corporate financial planning, budgeting, forecasting, and P&L reporting (including **non-IT** and **IT** booked actuals vs plan where modeled in OneStream).
2. **GL Sub Ledger (General Ledger Transactions)** — EBS General Ledger sub-ledger transactions: standardized, business-ready GL detail following data governance standards (**primary** source for **historical / booked IT spend** at transaction level).
3. **IT planning & TBM from Apptio** — ITPF and TBM-aligned marts for **IT-only** **forecast / future periods**, PO and contract scenario modeling, spend drivers, and application / service TCO views. **Do not** use these marts alone for “what did IT spend last quarter?” **actuals** questions — use **GL** or **OneStream Actual** per `aggregate/expensemaster/README.md`.
4. **Cloudability cloud spend mart** — Hyperscaler **cloud charges** ingested via Cloudability and enriched with OneStream cost center fields; **past-period cloud actuals** at mart grain. **Not** total company booked spend with those vendors on **GL**. Table choice, filters, and SQL → `aggregate/expensemaster/README.md`.

This unified view enables complete expense visibility from corporate budgets and GL detail through IT forecast and internal cloud charge analytics.

**Primary use cases:**
- **Expense Planning & Budgeting** → OneStream: Budget vs actual, expense forecasting, P&L, entity / cost center performance, variance vs plan
- **GL Transaction Analysis** → GL Sub Ledger: journal lines, sub-ledger detail, account balances
- **IT forecast & TBM** → ITPF / TBM marts inside ExpenseMaster: projected IT vendor spend, labor / asset / contract forecasts, PO impact, app and service cost pools (IT-only)
- **Hyperscaler cloud spend (actuals)** → Cloudability mart: past-period cloud spend by vendor, cost center, department

**When to route here:** Queries about corporate expenses, budgets, expense forecasts, expense planning, vendor spend, GL transactions, **historical IT spend**, **IT spend vs budget**, **IT forecast / future IT cost**, PO or contract planning impact in IT, spend-by-driver / app / service cost in IT, or past-period hyperscaler / cloud spend for internal Red Hat charge analytics.

**✅ ROUTE HERE when query contains:**
- **Expense keywords:** "expense", "expenses", "corporate expense", "spending", "expenditure", "cost management", "vendor spend"
- **Historical IT expense keywords:** "IT spend last quarter", "IT expenses for 2024", "actual IT costs", "IT spend history", "past IT expenses", "IT actuals"
- **IT forecast / IT planning keywords:** "IT spend forecast", "IT budget next year", "projected IT spend", "IT cost projection", "PO impact", "contract forecast", "spend driver", "application TCO", "service cost" (IT) — **ExpenseMaster** (ITPF/TBM section of README)
- **Cloud actuals keywords:** "cloud spend", "hyperscaler spend", "cloud accounts", "cloud cost by cost center", "cloud cost by department" — **ExpenseMaster** (Cloudability mart in README; **not** GL for the Cloudability slice; **not** Apptio for past actuals; **future** cloud forecast → Apptio within ExpenseMaster)
- **OneStream keywords:** "budget", "expense forecast", "expense plan", "P&L", "expense actual vs expense plan", "variance analysis", "entity performance", "cost center budget"
- **GL keywords:** "general ledger", "GL", "sub-ledger", "journal entry", "journal entries", "account balance", "GL transaction", "ledger transaction", "EBS GL"
- **Internal vendor / hyperscaler spend (RH operations):** "Red Hat AWS spend", "AWS spend last quarter", "AWS/Azure/GCP vendor spend" (with GL, actuals, cost center, ITPF, forecast, or corporate IT context), "Dell/Microsoft vendor spend" (internal IT actuals) — **ExpenseMaster**, not GTM or HG Insights

**❌ DO NOT route ExpenseMaster for:**
- Revenue data → Use **RevenueMaster**
- Bookings/ARR/ACV → Use **Bookingsmaster**
- Employee/org structure → Use **RoverPeople**
- Sales/opportunities → Use **Bookingsmaster**
- Employee expense reports/reimbursements → Not available in ExpenseMaster
- **Third-party company IT budgets** on RHSC accounts (modeled market view) → Use **GTM** or **HG Insights** as appropriate — not ExpenseMaster

**Data Scope & Coverage:**

*What IS in ExpenseMaster:*
- OneStream expense planning and budgeting data (budgets, expense forecasts, actuals, variance analysis)
- P&L (Profit & Loss) reporting and income statement data
- Entity and cost center expenses (expense actuals, expense forecasts, expense plans)
- GL Sub Ledger transactions from EBS (Oracle Enterprise Business Suite)
- Standardized GL transaction views following data governance standards
- Journal entries and account balances
- Budget vs actual comparisons and variance analysis
- Expense forecasting data
- Corporate expense tracking and analysis
- **IT planning & forecasting (ITPF) and TBM-style marts** (IT-only): modeled / forecast lines, contracts, labor, assets, IT vendor projections, app and service cost by pool or tower — **all in `expensemaster_db`** per deployment
- Cloudability-enriched hyperscaler cloud spend actuals

*What IS NOT in ExpenseMaster:*
- Revenue data → Use **RevenueMaster**
- Bookings/ARR/ACV → Use **Bookingsmaster**
- Employee expense reports/reimbursements → Not available
- Sales/opportunities → Use **Bookingsmaster**
- Employee/org structure → Use **RoverPeople**
- Lease data (e.g., RH tower leases) for IT — not in scope here; route per data product owner
- **Third-party / prospecting cloud budget** on RHSC accounts (modeled market view) → **GTM** or **HG Insights**, not the internal Cloudability mart
- Not all Apptio data is represented; for additional context contact TBMO@redhat.com or visit https://redhatit.apptio.com/


---

## Table guidance — two reads, found by search

`references/guidance/expensemaster/` holds 56 files, one rule or one
query template each, named for what it covers.

1. **`references/guidance/expensemaster/00-always-apply.md`** — the
   filters and exclusions that apply to every query against this
   product. Skipping it is how a statement runs clean and returns
   the wrong number.
2. **`grep` the directory for the business term, column or metric
   in the question** — "closed booking flag", "cost center
   hierarchy", "ACV_PLUS", "variance" — then read the one or two
   files that match. `glob` it instead if you would rather scan
   the names.

Never read the directory through. The query templates are working
SQL carrying the business filters that make the numbers correct;
adapt the closest one rather than writing fresh.
