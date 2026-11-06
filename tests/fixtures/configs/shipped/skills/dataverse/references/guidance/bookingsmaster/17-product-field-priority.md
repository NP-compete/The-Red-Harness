<!-- bookingsmaster · from 03-critical-business-rules-always-apply-2.md -->
### 10. Product Field Priority

**CRITICAL**: When querying for specific products, use the correct product field hierarchy.

**Priority Order** (use in this sequence):
1. **`product_split_offering_group`** - Primary product classification (standardized values)
2. **`product_split_offering_line`** - Secondary product detail (specific offerings)
3. **`product_split_offering_line_detail`** - Tertiary product detail (granular)

**❌ NEVER use CONTAINS/LIKE against `product_description` or `trx_name`** - This is unreliable and returns incorrect results.

**Examples**:
```sql
-- ✅ CORRECT - Use product_split_offering_group
WHERE product_split_offering_group = 'RHEL'
WHERE product_split_offering_group = 'OPENSHIFT'
WHERE product_split_offering_group = 'ANSIBLE'

-- ✅ CORRECT - Use product_split_offering_line for specific offerings
WHERE product_split_offering_line = 'SERVER'  -- RHEL Server
WHERE product_split_offering_line = 'OCP - OPENSHIFT CONTAINER PLATFORM'
WHERE product_split_offering_line = 'ANSIBLE AUTOMATION PLATFORM'

-- ❌ WRONG - Don't use CONTAINS/LIKE against descriptions or names
WHERE product_description ILIKE '%RHEL%'  -- Unreliable!
WHERE trx_name ILIKE '%Red Hat Enterprise Linux%'  -- Unreliable!
```

**Complete List of Product Offering Groups** (standardized values):

**Primary Groups**: RHEL, OPENSHIFT, ANSIBLE, APPLICATION SERVICES, CLOUD INFRASTRUCTURE, AI PLATFORMS, DATA, DATA AND AI, CONSULTING, TRAINING, MANAGEMENT AUTOMATION, INFRASTRUCTURE, MISCELLANEOUS, NULL

**Offering Lines by Group**:
- **RHEL** (10 lines): SERVER, SAP, SATELLITE, WORKSTATION, CERTIFICATE SYSTEM AND DIRECTORY SERVER, HIGH PERFORMANCE COMPUTING, HIGH AVAILABILITY, RESILIENT STORAGE, REAL TIME, MULTI-PRODUCT
- **OPENSHIFT** (24 lines): OPP - OPENSHIFT PLATFORM PLUS, OCP - OPENSHIFT CONTAINER PLATFORM, ACM - ADVANCED CLUSTER MANAGEMENT, OKE - OPENSHIFT KUBERNETES ENGINE, ROSA - RH OPENSHIFT ON AWS, ARO - AZURE RED HAT OPENSHIFT, OSD - OPENSHIFT DEDICATED, OVE - OPENSHIFT VIRTUALIZATION ENGINE, ACS - ADVANCED CLUSTER SECURITY, QUAY, DEVICE EDGE, DEVELOPER HUB, and 12 others
- **ANSIBLE** (4 lines): ANSIBLE AUTOMATION PLATFORM, MULTI-PRODUCT
- **APPLICATION SERVICES** (4 lines): Various middleware products
- **CLOUD INFRASTRUCTURE** (5 lines): Cloud infrastructure offerings
- **AI PLATFORMS** (5 lines): AI and ML platforms
- **DATA** (3 lines): Data services
- **MISCELLANEOUS** (3 lines): Other products
- **CONSULTING, TRAINING, MANAGEMENT AUTOMATION, DATA FOUNDATION, DATA AND AI, INFRASTRUCTURE**: No sub-classifications (use group level only)

---
