<!-- sfsaleslegacy · from 01-sfsaleslegacy-data-product-knowledge-bas.md -->
#### MARKETING_MARTS (13 Views) - **BUSINESS-FRIENDLY TRANSFORMED SCHEMA**
* **Purpose**: Architecturally unique, transformed schema with **business-friendly field names** and **marketing-specific analytical tools**. Only 65 columns vs 750 in other marts - heavily curated for marketing use cases.
* **Business Use Cases**: Campaign ROI analysis, Lead management, Marketing attribution, Funnel analysis
* **Architectural Transformation**:
  * **Field Renaming**: `id` → `opportunity_id`, `name` → `opportunity_name`, `amount` → `opportunity_amount`
  * **Field Filtering**: Strips technical Salesforce fields (no `opportunity_type_c`, custom fields)
  * **Performance Optimization**: 65 fields vs 750 in comprehensive marts
* **When to Use**: Select this mart exclusively for marketing-focused analysis:
  * Marketing Performance: Campaign ROI, lead conversion rates, funnel analysis
  * Lead Management: Lead lifecycle, routing, and qualification with **marketing_lead** table
  * Campaign Attribution: **marketing_campaign** and **marketing_campaign_member** analysis
  * **Supporting Tables Unique to Marketing**: marketing_lead, marketing_campaign, marketing_lead_management_history
  * **🚨 CRITICAL CONSIDERATIONS**:
  * **Incompatible Column Names**: Cannot directly join with other marts without field mapping
  * **Missing Technical Fields**: No `opportunity_type_c`, limited custom fields
  * **Use for Marketing Analytics Only**: Missing detailed line item, partner, and PSA context
