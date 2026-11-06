---
name: dataverse
description: >
  Everything Dataverse: data products and their contracts, and getting
  an actual figure out of the warehouse. Use for "what was Q4 ARR",
  "how many accounts churned", "who owns this data product", "what
  does this product promise" — anything answered from Dataverse.
---

# Dataverse

**Purpose:** One skill for Dataverse — the products, and the numbers.
Return the figure, not instructions for obtaining it.

Getting a figure is four stages: **identify the data product →
shortlist the tables → write the SQL → execute it.** You do the
first three here, from the route table and the curated guidance.
Only the last one is a tool.

- **`dataverse_execute_sql`** — runs a Snowflake statement, returns
  rows. Choosing the product, the tables and the SQL is yours.
- **`dataverse_create_chart_app`** — draws rows you already have.
  Use it when the shape is the point, not for a single figure.
- **`dataverse_search_dataversehelp`** — platform "how do I"
  questions, not figures.

## Search the guidance, do not read it

1. **Route** with the table below. The user naming a product settles
   it — respect it even if another looks closer.
2. **Read `references/products/<product>.md`** — scope, the routing
   cautions, and what that product's guidance covers. One read.
3. **Read `references/guidance/<product>/00-always-apply.md`** where
   it exists — the filters and exclusions that hold for every query
   against that product, and the ones a targeted search will not
   surface. Skipping it is how a statement runs clean and returns
   the wrong number.
4. **`grep` `references/guidance/<product>/` for the business term,
   column or metric in the question** — "closed booking flag",
   "cost center hierarchy", "ACV_PLUS", "variance". That directory
   is one rule or one query template per file, named for what it
   covers, so the match list usually decides it on its own.
5. **Read the one or two files that matched.** The query templates
   are working SQL carrying the business filters (booking flags,
   origin-system exclusions) that are not in Atlan and not
   guessable; without them a query runs clean and returns nothing.
   Adapt the closest template rather than writing fresh.
6. **Confirm the real column names in Atlan** (`semantic_search_tool`,
   then `get_assets_tool`) — assumed names are the largest single
   cause of failed statements — then run it.

**Structure and meaning come from Atlan, never from the warehouse.**
Which tables a product has, which columns they carry, what a column
means, its type, owner and classification — all catalogue
questions, answered in one call against live metadata. Search by
meaning: people ask for "churn" and the asset is
`dim_acct_lifecycle_v3`.

The guidance files are a snapshot of *how to query*, not an
inventory — they name the columns a template needs and nothing
else. So for "what is in this product", "what does this column
mean", "which table has the renewal date", go to Atlan, not to a
grep. Never `SELECT *` or `DESCRIBE TABLE` to learn a shape, and
never read a row to describe a field: sampling a production
warehouse is slow, costs money, and tells you ten values rather
than what the column is for. `dataverse_execute_sql` is for the
figure that was asked for, once Atlan has said what you are
querying.

**Never read a guidance directory through, and never read a file
just because its name sounds mandatory.** Those directories hold
40–90 KB per product; a `grep` reaches the one rule that applies for
a fraction of it. If a grep returns nothing useful, widen the term
or `glob` the directory to scan the names — do not fall back to
reading everything.

Only open `references/routing.md` when the table below genuinely
does not decide it, `references/routing-sales-intent.md` (+ `-2`)
for pipeline vs bookings vs revenue vs discounting, and
`references/routing-spend-intent.md` for internal vs market spend.

## Routing

| Question is about | Product |
|---|---|
| Bookings, ARR, ACV, TCV, opportunities, pipeline, deal history | `bookingsmaster` |
| Recognised/GL revenue, revenue by geo, service or subscription revenue | `revenuemaster` |
| Discount %, MSRP vs TCV, list vs actual price | `discounting` |
| Corporate and IT spend, GL, budget vs actual, vendor and cloud actuals, ITPF/TBM forecast | `expensemaster` |
| Pipeline coverage, velocity, waterfall, ASP, product cohort retention | `forecasting` |
| Renewal pipeline and ACV, new-vs-renewal | `renewals` |
| Sales targets, quotas, restated renewals | `sales-planning` |
| Commission, incentive plans, territory credit | `si-execution` |
| Employees, managers, org chart, headcount in a cost centre | `roverpeople` |
| Cost-centre *financial* ownership, finance managers, departments under an org | `fammatrix` |
| Account intelligence, buyer intent, cross-sell targeting, competitive footprint of **our** accounts | `gtm` |
| Market technographics, TAM, which companies use a product | `hginsights` |
| Customer segmentation, GSG/SG hierarchy, account flags | `saleshierarchy` |
| EBS ↔ RHSC identifier mapping | `rosettastone` |
| MDM party master, hierarchy, addresses | `mdmparty` |
| MDM product master, SKU hierarchy, pricing tiers | `mdmproduct` |
| Product catalogue and attributes (reference) | `official-product-list` |
| Offering lifecycle, SKU leverage, OLM | `offering-lifecycle-management` |
| Partner claims, rebates, credentials, transaction-journal failures | `partner-programs` |
| EDS codes, SIC codes, industry hierarchy | `srcdatagovernance` |
| Jira projects, issues, sprints | `jira` |
| Adobe web analytics, campaign attribution | `adobe` |
| Agent latency, LLM cost, Langfuse traces | `agenthealth` |
| "How do I" Dataverse platform and tooling questions | `dataversehelp` |
| Salesforce sales data | `sfsales` |
| Legacy Salesforce — **only** when the user says "legacy" (frozen data) | `sfsaleslegacy` |

Two traps worth naming: **the word "revenue" in any form means
`revenuemaster`, never `bookingsmaster`**, and **who *financially*
manages a cost centre is `fammatrix`, who *reports to* whom is
`roverpeople`** — an org-level headcount question needs both.

Also available: `grokket`, `intelligentaccess`, `key-routing-key-words`,
`data-scope-coverage`.

## Writing the SQL

Snowflake, read-only, immediately executable. Date filtering,
identifier handling, join and CTE limits, and what to do when a
statement fails are in `references/sql-style.md` — the rules about
never altering a user's identifiers and never reshaping a supplied
list are the ones that silently corrupt an answer.

**One statement per question.** Every execution is seconds of
warehouse time the reader waits through, so get the whole answer in
one:

- **No probe queries.** Do not count rows, check a filter matches,
  or look at the distinct values of a column before the real query.
  Atlan already told you the shape; the first statement you run
  should be the one that answers the question.
- **Fold facets into one statement.** By geo *and* by quarter is one
  `GROUP BY`, not two runs. Several metrics over the same rows are
  several aggregates in one `SELECT`. Two periods compared are
  conditional aggregation or one CTE each, not two round trips.
- **Do not re-run to narrow or reformat.** Returned more than you
  needed, or in the wrong order? Say the answer from the rows you
  have. Re-running for presentation spends the warehouse on
  something you can do in the reply.

**Two corrective attempts after a failure, then stop.** That budget
is for *errors*, not refinement. The error is the feedback: read it,
look the name up in Atlan, fix the cause. A third attempt is usually
the same mistake rearranged.

## Guardrails

- **Read-only.** `SELECT` and CTEs. Never `INSERT`, `UPDATE`,
  `DELETE`, `MERGE`, `CREATE`, `DROP` or `GRANT`, whatever the user
  asks for — this is a production warehouse.
- **Never hand back SQL instead of an answer.** If you can run it, run
  it.
- **Say where the figure came from** — the table, the filters, the
  period. These are financial figures people will repeat.
- **State what the figure is not.** A snapshot is not a trend;
  bookings ARR is not recognised revenue. If two readings of the
  question give different numbers, say so and give the one you chose.
- **Do not present an empty result as zero.** No rows usually means
  the filter is wrong, not that the business is empty.
- **If Dataverse is not connected, stop.** The whole answer is
  "I cannot answer this without Dataverse." Do not say how to
  connect it; the interface already does, in the reader's own
  language. No routing, no guidance reads, no SQL you cannot run.

## Output

```
**<Answer, with the figure in bold and its units.>**

- **Source.** <database.schema.table>
- **Filters.** <the period and conditions that define the number>
- **Caveats.** <only when they change how the number should be read>
```

Three lines, not a report.
