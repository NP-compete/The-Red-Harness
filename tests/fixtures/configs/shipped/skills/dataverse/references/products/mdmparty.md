### **MDMPARTY**
**Database:** `mdmparty_db`
**Schema:** `partylens_marts` (authoritative analytics mart; legacy `marts` is being decommissioned — do not use for new queries)
**Maturity:** AI Experimental for selected models — confirm with the data product owner before executive reporting.

**Build (dbt):** Party Lens objects are implemented in the **mdmparty-dbt** project under `models/partylens_marts/` and deploy to **`mdmparty_db.partylens_marts`**. The **party** and **address** dimensions are loaded as **full-refresh tables** from Party Service staging (`stg_mdm_party_lens_party`, plus **DUNS hierarchy** from `stg_mdm_party_lens_duns_relation`); each keeps the **latest `ingested_time` per party `legacy_id`**, requires **`ACTIVE`** status and **`merged_with` null**, and the dimension **deduplicates on DUNS** (one surviving row per non-null DUNS). **`mdm_party_lens_relation_flattened_v1`** and **`mdm_party_lens_merged_businessid_v1`** are **full-refresh tables** without the `experimental` tag (merge mart unions **current** merge state with **`raw_party.party_merge`** history). Role, D&B, alias, alternate, and intercompany marts are typically **views** that take the **latest `ingested_time` per source row `id`** from their staging models. Models tagged **`experimental`** in dbt are higher-change; validate for executive use.

**MDMPARTY** is the source-aligned customer and business-entity master for Red Hat (customers, partners). **All consumption for this data product is `mdmparty_db.partylens_marts`** (for example `party_lens_dim_v1` for party profile and hierarchy, plus addresses, alternates, aliases, roles, intercompany relationships, and D&B satellite tables). Legacy objects in **`mdmparty_db.marts`** (e.g. `party_dim`) are **not** the target architecture; migrate workloads to the `party_lens_*` / `mdm_party_lens_*` equivalents.

**Primary use cases:** Party lookup and profiling, corporate hierarchy (parent / domestic ultimate / global ultimate), addresses and firmographics, alternate identifiers, customer vs partner roles, intercompany relationships, D&B-enriched attributes, data-quality and golden-record patterns.

**`party_lens_party_role_v1`:** In Snowflake, **`role_type`** is stored in **title case** — filter with **`'Customer'`** and **`'Partner'`** (uppercase literals like `'CUSTOMER'` match nothing).

**When to route here:** Queries about **MDM party**, **MDMPARTY**, **golden party**, **party master**, **`mdm_party_id`**, DUNS/hierarchy at party level, party addresses, or cross-system party identifiers **when the scope is party master data**. See **`source/mdmparty/README.md`** for SQL patterns against **`partylens_marts`**.

**Data Scope & Coverage:**

*What IS in MDMPARTY (`mdmparty_db.partylens_marts`):*
- Party name and address
- Party roles
- Party partner role classifications
- Party partner role modules
- Party aliases (names)
- Party alternate identifiers (IBM Site ID)
- Party D&B industry classification
- Party D&B finance
- Party D&B tax
- Party D&B phone
- Party D&B hierarchy (parent, domestic ultimate, global ultimate)
- Party intercompany list and relationships

*What IS NOT in MDMPARTY (route elsewhere):*
- **EBS ↔ RHSC golden account mapping** → Use **Rosettastone**
- **Bookings, ARR, ACV, pipeline, opportunities** → Use **Bookingsmaster**
- **Recognized revenue** → Use **RevenueMaster**
- **RHSC account intelligence (flags, intent, GTM audiences)** → Use **GTM**

**KEY ROUTING RULES:**
- **"MDM party"** / **"party master"** / **`mdm_party_id`** / **"party hierarchy"** / **"party address"** / **"party identifiers"** → **MDMPARTY** — **`mdmparty_db.partylens_marts`**
- **`party_lens_*`** / **`mdm_party_lens_*`** / **`partylens_marts`** → **MDMPARTY** — **`mdmparty_db.partylens_marts`**
- **Legacy `party_dim` / `marts` in docs or old reports** → **MDMPARTY** — **rewrite against `partylens_marts`** (`party_lens_dim_v1`, etc.); **`marts` is decommissioned**
- **"Map EBS to RHSC"** / **golden account mapping** (without party-master-only scope) → **Rosettastone**, not MDMPARTY alone

---
