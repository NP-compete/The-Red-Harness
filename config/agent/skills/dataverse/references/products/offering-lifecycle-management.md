### **Offering Lifecycle Management (OLM)**
**Database:** `offeringlifecyclemgmt_db`
**Schema:** `marts`
**Maturity:** AI Experimental

Offering Lifecycle Management (OLM) provides a unified **SKU-level** view of Red Hat offering lifecycle status: catalog attributes, MSRP, offering taxonomy, pipeline-derived activeness, subscription coverage, leverage and inactivation signals, and current/prior-quarter commercial metrics (ARR/ACV/TCV-style) for lifecycle decisions.

**Primary use cases:** Count or list active catalog SKUs; identify leveraged vs inactivation-candidate SKUs; rank SKU performance within offering groups; subscription coverage counts; ARR rollups by offering taxonomy; first revenue-recognition timing per SKU.

**When to route here:** Queries about **OLM**, **offering lifecycle**, **SKU** performance or lifecycle status, **MSRP** on the OLM mart, **quoting tier**, leveraged/unleveraged SKUs, latest-closed-quarter ARR at SKU grain, subscription coverage on the mart, or offering-group/line analytics.

**❌ DO NOT route here for:**
- **Corporate product catalog** (aliases, components, reference lifecycle without OLM mart metrics) → **Official Product List**
- **Opportunity- or account-centric pipeline** beyond SKU rollups → **Bookingsmaster**
- **Recognized GL revenue** → **RevenueMaster**
- **Deal net price / CPQ discounts** → **Discounting** or transactional products as appropriate
- **Enterprise-unique customer counts** by summing SKU-level customer fields → Not supported on this mart

**Data Scope & Coverage:**

*What IS in OLM:*
- One row per **SKU** with catalog, MSRP, taxonomy, leverage/unleveraged flags, subscription coverage, pipeline-derived current/prior-quarter metrics, and related activeness fields

*What IS NOT in OLM:*
- Full corporate product catalog reference tables → **Official Product List**
- Raw bookings / opportunity exploration → **Bookingsmaster**
- GL recognized revenue → **RevenueMaster**

**KEY ROUTING RULES:**
- **"OLM"** / **"offering lifecycle"** / **"leveraged SKU"** / **"inactivation candidate"** → **OLM**
- **"Latest closed quarter ARR"** at SKU grain (OLM context) → **OLM**
- **"Product catalog"** without SKU lifecycle metrics → **Official Product List**

---
