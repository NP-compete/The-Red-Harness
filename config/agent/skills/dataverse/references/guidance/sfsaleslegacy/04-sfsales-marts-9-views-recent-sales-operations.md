<!-- sfsaleslegacy · from 01-sfsaleslegacy-data-product-knowledge-bas.md -->
#### SFSALES_MARTS (9 Views) - **RECENT SALES OPERATIONS**
* **Purpose**: Focused sales operations mart optimized for **current and recent sales activities**. Streamlined for operational performance without historical depth complexity.
* **Business Use Cases**: Current GTM Operations, Recent Sales Performance, Active Pipeline Analysis, Real-time Territory Management
* **When to Use**: Select for **recent/current sales operations**:
  * Current Product Mix Analysis: Recent opportunity and product coverage
  * Active Pipeline Management: Current sales operations and metrics
  * Recent Overlay Credit Analysis: Current period credit tracking
  * Operational Sales Metrics: Day-to-day sales performance monitoring
  * **Key Views**:
  * sfsales_opportunity: The master opportunity view with all 752 fields.
  * sfsales_opportunity_line_item, sfsales_opportunity_partner: Detailed opportunity components.
  * sfsales_contact, sfsales_address, sfsales_user: Core CRM objects.
  * sfsales_ebs_account: Critical financial integration with Oracle EBS.
  * sfsales_expiring_product: Foundational renewal and subscription management.
  * sfsales_product: The master product catalog.
  * **Critical Considerations**:
  * These views are comprehensive, unfiltered pass-throughs from staging using standard Salesforce technical field names.
  * Like GENERAL_MARTS, these views are very wide. Be specific in your column selection.
