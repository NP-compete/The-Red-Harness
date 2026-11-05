### **SrcDataGovernance**
**Database:** `srcdatagovernance_db`
**Maturity:** AI Experimental


Centralized repository for enterprise data standards and reference data that ensures consistency across data products and business systems. Provides standardized codes, descriptions, and classifications used throughout Red Hat's data ecosystem.

**Primary use cases:** Enterprise data standards lookup, industry classification reference, SIC code mapping, and standardized code validation for data governance.

**When to route here:** Queries about enterprise data standards (EDS) codes, standardized code descriptions, industry hierarchy classifications, SIC (Standard Industrial Classification) codes, reference data lookups, or data governance standards.

**Data Scope & Coverage:**

*What IS in Source Data Governance:*
- Enterprise Data Standards (EDS) with reference data - standardized codes and descriptions (e.g., billing_block, delivery_block, credit_block)
- Industry hierarchy - Red Hat's proprietary industry classification system (Industry → SubIndustry → Vertical)
- SIC reference data - Standard Industrial Classification codes with Red Hat industry mappings
- Standardized code lookups - active codes with descriptions for data validation
- Industry to SIC mappings - Red Hat industry verticals mapped to standard SIC codes
- Reference data for data quality and compliance

*What IS NOT in Source Data Governance:*
- Conceptual EDS standards without reference data (e.g., Annual Recurring Revenue, Customer Number, Email Address, Postal Code) - these are defined standards but don't have lookup codes
- Actual business transaction data → Use appropriate operational data products
- Employee or organizational data → Use **RoverPeople**
- Revenue data → Use **RevenueMaster** (NOT Bookingsmaster)
- Sales/bookings data → Use **Bookingsmaster** (NOT RevenueMaster)
- IT cost data → Use **Expensemaster**

**🔑 KEY DISTINCTION:**
- **EDS with reference data** (has codes/values) → Query `ibm_enterprise_data_standards` table
- **Conceptual EDS** (no reference data) → Explain that the standard is defined but doesn't have lookup codes in this data product

---
