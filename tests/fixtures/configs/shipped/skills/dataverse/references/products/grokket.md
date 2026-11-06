### **Grokket**
**Database:** `grokket_db`
**Schema:** `marts`
**Maturity:** `AI Experimental`
**Detailed guidance:** `aggregate/grokket/README.md`

Grokket provides **RHEL usage and telemetry** from customer systems where **Lightspeed (Insights)** and/or **RHSM (Subscription Manager / Candlepin)** data sharing is enabled—**monthly system check-ins**, footprint and version mix, and **workload / software fingerprints** (nightly matching on installed RPMs and running processes; fingerprint enrichment is **Lightspeed-sourced**). **`FLEET_FOCUS_MART`** supports general fleet questions; **`PROD_GROKKET_MASKED`** adds **installed / running workload** signals (larger—always filter **`DATACAPTURE_MONTH`** and **`MONTH_FLAG`**). Do **not** query fingerprint-definition catalog tables for routing—use **`PROD_GROKKET_MASKED`** workload columns for host-level software signals.

**Primary use cases:** RHEL adoption by **version**, **footprint**, **hypervisor**, **hyperscaler**, **public cloud**; **workload / software** presence from fingerprints; **geo / segment / industry** rollups for telemetry-connected populations; **telemetry coverage** messaging (partial estate—see README).

**When to route here:** Questions about **RHEL telemetry**, **RHEL usage**, **systems by RHEL version**, **bare metal vs VM vs public cloud** mix, **workloads installed or running**, **RPM / process fingerprints**, **Grokket**, or **Insights + RHSM** fleet behavior—**not** customer-identified usage pulls or non-RHEL platforms as the primary scope.

**⚠️ CRITICAL GUARDRAILS:**
- **NOT Ansible or OpenShift telemetry** as the primary scope → route to the correct product for those platforms.
- **NOT customer-level usage** lists or ad-hoc **named customer** usage exports.
- On **`PROD_GROKKET_MASKED`**, self-service SQL must **not** return restricted identifiers: **`ACCOUNT_NAME`**, **`EBS_ACCOUNT_NUMBER`**, **`GLOBAL_SALES_GROUP_NAME`**, **`ACCOUNT_ID`**—use **`GEO`**, **`SEGMENT`**, **`INDUSTRY`**, version/footprint dimensions instead.
- Always state **telemetry coverage is partial** (telemetry-enabled customers/systems only—see **`aggregate/grokket/README.md`**).

**🎯 GROKKET vs. GTM vs. HG Insights (high level):**
- **Grokket** = **Actual RHEL system telemetry** (what is running / installed on subscribed telemetry-connected systems).
- **GTM** = **RHSC account intelligence** (flags, intent, revenue potential, technographics matched to accounts)—not a substitute for fleet telemetry mart detail.
- **HG Insights** = **Third-party market / IT budget / technographics** across a broad company universe—not Red Hat operational telemetry.

**✅ Route here when query contains:**
- "RHEL usage", "RHEL telemetry", "Grokket", "Insights", "RHSM", "Lightspeed" (fleet context)
- "RHEL systems by version", "RHEL footprint", "bare metal", "VMware", "hyperscaler", "public cloud", workload/fingerprint language ("installed workloads", "running workloads", "fingerprints", "RPMs installed")

**❌ Do NOT route here when query contains:**
- Ansible or OpenShift as the **primary** subject (use the appropriate product)
- **Named customer** / **account-level RHEL usage** from telemetry (out of scope for self-service)
- "Bookings", "pipeline", "ARR" as primary intent → **Bookingsmaster** / **GTM** as appropriate

**Data Scope & Coverage:**

*What IS in Grokket (`grokket_db.marts`):*
- **`FLEET_FOCUS_MART`** — deduplicated **system-month** style fleet facts (**`DMI_SYSTEM_UUID`**) from **Lightspeed + RHSM**, with version, footprint, cloud, hypervisor, and demographic rollups where present.
- **`PROD_GROKKET_MASKED`** — fleet fields plus **workload / fingerprint** columns for software detection (use for **fingerprint** questions; expect larger scans).

*What IS NOT in Grokket:*
- Full estate of all RHEL customers (telemetry-disabled customers are absent)
- **Customer-identified** usage exports from **`PROD_GROKKET_MASKED`** (restricted columns)
- Ansible / OpenShift platform telemetry as **product scope**

**🔑 KEY ROUTING RULES:**
- **Fleet only** (version, footprint, cloud, geo, segment, demographics) → **`FLEET_FOCUS_MART`**
- **Workload / application / fingerprint / installed vs running** → **`PROD_GROKKET_MASKED`** (with time filters). Do **not** query fingerprint-definition catalog tables.

---
