<!-- fammatrix · the rules that apply to every query here -->
# Always apply — fammatrix

Read this before writing any SQL for this product. Everything
below applies regardless of what the question asks.

### ⚠️ CRITICAL: Product Name → Department Mapping

Department names in the DEPT hierarchy **do not always match** the product names users ask about. For example, OpenShift lives under `Hybrid_Platforms_BU` (BU side) and `RnD_Hybrid_Platforms` (Engineering side) — the word "OpenShift" does not appear in any DEPT column at any level.

When a user asks "Who runs [product]?", use the tables below to find the correct DEPT values to search. Both tables are sourced from the CY26 Product Strategy.

**BU / Product Management side** (DEPT_2 = `Products`, search at DEPT_3):

| DEPT_3 | Product Keywords (what users say) |
|---|---|
| `Hybrid_Platforms_BU` | OpenShift, Red Hat OpenShift, Red Hat OpenShift Container Platform, OCP, OpenShift Virtualization, CNV (Container Native Virtualization), OKE (OpenShift Kubernetes Engine), ACS (Advanced Cluster Security), ACM (Advanced Cluster Management), ROSA (Red Hat OpenShift on AWS), ARO (Azure Red Hat OpenShift), OSD (OpenShift Dedicated), Quay, Red Hat Developer Hub, StackRox, Red Hat OpenStack Services on OpenShift, Hybrid Platforms, RHADS (Red Hat Advanced Developer Services), Konflux |
| `RHEL_Platforms_BU` | RHEL, Red Hat Enterprise Linux, Satellite (Red Hat Satellite), RHEL Lightspeed, Image Mode, Podman Desktop, RHEL SDK |
| `RHEL_Artificial_Intelligence_BU` | RHEL AI, Red Hat Enterprise Linux AI |
| `Artificial_Intelligence_BU` | Red Hat AI, OpenShift AI, Red Hat AI Inference Server, Red Hat OpenShift AI |
| `Ansible_BU` | Ansible, AAP (Ansible Automation Platform), Red Hat Ansible Automation Platform, EDA (Event-Driven Ansible), ALIA (Ansible Lightspeed Intelligent Assistant) |
| `Application_Developer_BU` | Application Services, EAP (Red Hat JBoss Enterprise Application Platform), OpenJDK, 3scale (Red Hat 3scale API Management), Apache Camel, AMQ, Kafka (Streams for Apache Kafka), Debezium |
| `Application_Runtimes` | Application Runtimes, Red Hat Application Runtimes |
| `Hybrid_Cloud_Experience` | Hybrid Cloud Console, HCC, Red Hat Lightspeed, Red Hat Insights, Cloud Marketplaces, Subscription Management, HCS (Hybrid Committed Spend) |
| `In_Vehicle_OS` | RHIVOS (Red Hat In-Vehicle Operating System), In-Vehicle OS |
| `Edge` | Edge, Edge Computing |
| `Portfolio_Product_Marketing` | GLS (Global Learning Services), Red Hat Training and Certification, Portfolio |

**Engineering / R&D side** (DEPT_2 = `Global_Engineering`, search at DEPT_3 or DEPT_5):

| DEPT level | DEPT value | Product Keywords (what users say) |
|---|---|---|
| DEPT_3 | `AI_Engineering` | OpenShift AI, Red Hat OpenShift AI, InstructLab, Red Hat AI Inference Server |
| DEPT_5 | `RnD_Hybrid_Platforms` | OpenShift, Red Hat OpenShift, OCP, OpenShift Virtualization, CNV (Container Native Virtualization), OpenShift Observability, StackRox, Migration Tooling |
| DEPT_5 | `RnD_Core_Platforms` | RHEL, Red Hat Enterprise Linux, RHIVOS, OpenStack, R&D Platform |
| DEPT_5 | `RnD_Ansible_Engineering` | Ansible, AAP (Ansible Automation Platform) |
| DEPT_5 | `RnD_Middleware_n_App_Services` | Application Services, Middleware, EAP, Runtimes |
| DEPT_5 | `RnD_Hybrid_Cloud_Management` | Hybrid Cloud Console, HCC, Console.dot, SRE |
| DEPT_5 | `RnD_Portfolio_n_Delivery` | Developer Hub, Developer Tools, Secure Flow |

**How to use:** When a user asks "Who runs OpenShift?", look up "OpenShift" in the Product Keywords columns → find `Hybrid_Platforms_BU` (BU side) and `RnD_Hybrid_Platforms` (Engineering side) → query fammatrix with `WHERE DEPT_3 = 'Hybrid_Platforms_BU' OR DEPT_5 = 'RnD_Hybrid_Platforms'` to get both BU and Engineering leadership.

**⚠️ Disambiguation Notes:**

- **"Lightspeed"**: Two different products share this name. **RHEL Lightspeed** is an AI-powered intelligent assistant for RHEL 10 (`RHEL_Platforms_BU`). **Red Hat Lightspeed** (formerly Insights) provides operational visibility and cost management across RHEL and OpenShift (`Hybrid_Cloud_Experience`). If the user says just "Lightspeed" without context, ask which one they mean.
- **Application Services**: Engineering and Product functions transferred to the IBM Runtimes organization effective July 1, 2025. Red Hat retains GTM, marketing, and customer support. The `Application_Developer_BU` and `Application_Runtimes` entries in fammatrix may not reflect current engineering ownership.

### ⚠️ CRITICAL: Departments at DEPT_4 / DEPT_5 (NOT at DEPT_3)
Some commonly searched departments exist at deeper levels, NOT at DEPT_3:

| Department | User Might Say | Actual Level | Values | Path |
|---|---|---|---|---|
| IT | "IT", "Information Technology" | DEPT_4: `IT_IBM`, `IT_IBM_RH`; DEPT_5: `IT_RH` (34 CCs) | `CORP → GnA_Consol_IBM_RH → GnA_RH → COO_RH → IT_RH` |
| PPL / People / HR | "People", "HR", "PPL" | DEPT_4: `PPL_IBM`, `PPL_IBM_RH`; DEPT_5: `PPL_RH` (8 CCs) | `CORP → GnA_Consol_IBM_RH → GnA_RH → COO_RH → PPL_RH` |
| BSO | "BSO", "Business Strategy & Operations" | DEPT_5: `BSO_RH` (12 CCs) | `CORP → GnA_Consol_IBM_RH → GnA_RH → COO_RH → BSO_RH` |
| Finance | "Finance", "FnA" | DEPT_4: `FIN_IBM` (4 CCs) | `CORP → GnA_Consol_IBM_RH → GnA_IBM → FIN_IBM` |
| Legal | "Legal", "LBA" | DEPT_4: `LBA_IBM`, `LBA_IBM_RH` | `CORP → GnA_Consol_IBM_RH → GnA_IBM_RH → LBA_IBM_RH` |
| Facilities | "Facilities", "FAC" | DEPT_5: `FAC_IBM_RH` (96 CCs) | `CORP → GnA_Consol_IBM_RH → GnA_IBM_RH → GWS_IBM_RH → FAC_IBM_RH` |

**CRITICAL:** When searching for any of these departments, do NOT assume DEPT_3. Always search across ALL department levels using **Pattern 11** below.

---
