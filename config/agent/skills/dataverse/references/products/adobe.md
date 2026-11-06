### **Adobe**
**Database:** `adobe_db`
**Schema:** `marts`
**Maturity:** AI Experimental

Adobe Analytics data product providing hit-level web analytics for Red Hat's digital properties. The `adobe_mrktng` mart exposes marketing touchpoints, campaign attribution, and visitor analytics from Adobe Analytics (via Fivetran).

**Primary use cases:** Web analytics, marketing touchpoints, campaign attribution, session/visit analytics, geographic and device analytics from Adobe.

**When to route here:** Queries about Adobe Analytics hit data, web analytics, page views, sessions, marketing touchpoints, campaign performance (Adobe), visitor/geo/device analytics from Adobe.

**Data Scope & Coverage:**

*What IS in Adobe (adobe_mrktng):*
- Hit-level Adobe Analytics data (page views, events, visits)
- Marketing touchpoint identifiers (`marketing_touchpoint_id`, `adobe_session_id`)
- Campaign and channel dimensions (`post_campaign`, `post_channel`)
- Geographic dimensions (`geo_country`, `geo_region`, `geo_city`)
- Device/browser dimensions (`browser`, `os`, `connection_type`)
- Red Hat SDR eVars (e.g., `post_evar_1` = Page Name)
- Visit/session flags (`new_visit`, `daily_visitor`, `mcvisid`, `visit_num`)

*What IS NOT in Adobe (route elsewhere):*
- Email campaign data → Use **Marketo**
- CRM/lead data → Use **Marketo** or **Salesforce**

**KEY ROUTING RULES:**
- **"Adobe Analytics..."** / **"Web analytics..."** / **"Marketing touchpoints..."** → **Adobe** (`adobe_mrktng`)
- **"Email campaigns..."** / **"Marketo..."** → **Marketo**

---

## Table guidance — two reads, found by search

`references/guidance/adobe/` holds 8 files, one rule or one
query template each, named for what it covers.

1. **`references/guidance/adobe/00-always-apply.md`** — the
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
