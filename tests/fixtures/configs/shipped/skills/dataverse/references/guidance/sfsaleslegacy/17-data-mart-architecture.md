<!-- sfsaleslegacy · from 05-universal-architectural-patterns-best-pr.md -->
### Data Mart Architecture
The database is organized into domain-specific schemas (marts) that follow one of two primary architectural patterns:

* **Comprehensive Pass-Through (Default)**: Most marts (GENERAL_MARTS, SFSALES_MARTS, ENTERPRISEAPPLICATION_MARTS, PSA_MARTS) are complete, unfiltered representations of the source data. They preserve all original fields and technical names (e.g., field_name__c). These marts are extremely wide and require you to be highly selective with your column choices.
* **Curated & Transformed (Marketing)**: The MARKETING_MARTS schema is the only one that is highly curated. It aggressively selects a small subset of fields, renames them to be business-friendly (e.g., id becomes opportunity_id), and applies transformations (e.g., the partner_flag).

### Field Naming Conventions
* **Standard (Most Marts)**: Fields retain their technical Salesforce names, with custom fields ending in __c.
* **Marketing Aliases**: The MARKETING_MARTS schema uses intuitive, business-friendly names. This is a critical distinction. When joining a marketing view to a view from another mart, you must map the aliased names back to their original technical names.
