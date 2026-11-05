<!-- sfsaleslegacy · from 01-sfsaleslegacy-data-product-knowledge-bas.md -->
## SFSALESLEGACY Data Product Knowledge Base

**Database**: SFSALESLEGACY_DB
**Universal Filters**: `is_deleted = 0 AND _fivetran_active = 1` (Apply to ALL queries unless explicitly told otherwise).
**Architecture**: All marts are built as views. Be mindful of join performance.

### Schema (Mart) Overviews & Selection Logic

**🎯 CRITICAL ARCHITECTURAL INSIGHT**: All marts contain **identical core opportunity data** (4.86M records). The difference is in **domain-specific supporting tables** and **analytical contexts** designed for specific business functions.
