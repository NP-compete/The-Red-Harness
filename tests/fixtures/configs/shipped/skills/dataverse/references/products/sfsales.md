### **Salesforce Sales (SFSALES)**
**Database:** `sfsales_db` (`sfsales_marts`)

Red Hat's live CRM: the sales process from lead to closed-won —
opportunities, pipeline, accounts, territories and partner channel
activity, with record-type segmentation and stage management.

**When to route here:** Salesforce objects themselves — opportunity
records, account and contact relationships, sales stages, territory
and team assignment, partner-driven deals.

**Do not route here for:** the *bookings figure* for a period
(`bookingsmaster`, which is built on this) or recognised revenue
(`revenuemaster`). SFSALES is the CRM record; Bookingsmaster is the
reconciled, filtered number. Use `sfsaleslegacy` only when the user
says "legacy" — that data is frozen.

## Table guidance — two reads, found by search

`references/guidance/sfsales/` holds 16 files, one rule or one
query template each, named for what it covers.

1. **`references/guidance/sfsales/00-always-apply.md`** — the
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
