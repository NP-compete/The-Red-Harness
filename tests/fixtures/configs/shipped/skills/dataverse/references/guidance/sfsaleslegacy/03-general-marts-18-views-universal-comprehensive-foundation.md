<!-- sfsaleslegacy · from 01-sfsaleslegacy-data-product-knowledge-bas.md -->
#### GENERAL_MARTS (18 Views) - **UNIVERSAL COMPREHENSIVE FOUNDATION**
* **Purpose**: The universal, cross-domain foundation providing **the most comprehensive analytical ecosystem**. Contains unique tables not available elsewhere: CPQ (Apttus), document management, contracts, **credit processing**.
* **Business Use Cases**: Legal research, compliance audits, complex deal analysis, document management, CPQ analysis, cross-functional reporting, **financial terms analysis**
* **Real Business Requirements**:
  * **Credit Processing & Payment Terms**: **CRITICAL** - Contains authoritative payment terms through credit approval workflows (GENERAL_CREDIT table unique to GENERAL_MARTS)
  * **Legal & Compliance**: Historical contracts, order forms, approvals, audit trails, transaction documents
  * **CPQ Analysis**: Apttus proposal and quote management (unique to GENERAL_MARTS)
  * **Document Management**: Content documents, attachments, file versioning (unique to GENERAL_MARTS)
  * **Audit & History**: Comprehensive change tracking and field history
* **When to Use**: Select for comprehensive analysis requiring unique tables:
  * **Payment Terms Analysis**: **MANDATORY** for payment terms queries - contains authoritative credit approval data (general_credit)
  * **CPQ & Quoting**: Apttus proposal analysis (general_apttus_proposal_proposal, general_apttus_proposal_proposal_line_item)
  * **Document Research**: Contract documents, order forms, approvals (general_content_document, general_attachment)
  * **Credit Analysis**: Credit processing and adjustments (general_credit)
  * **Contract Management**: Contract lifecycle and terms (general_contract)
  * **Cross-functional Analysis**: Questions spanning multiple business domains
  * **Audit Requirements**: Historical change tracking (general_opportunity_history, general_opportunity_field_history)
* **Critical Considerations**:
  * **Widest Tables**: 750+ columns require explicit column selection
  * **Performance Impact**: Most comprehensive but potentially slower due to complexity
  * **Unique Supporting Tables**: Only mart with CPQ, document management, contracts, credit processing
