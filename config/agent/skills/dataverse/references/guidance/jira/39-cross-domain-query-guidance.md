<!-- jira · from 04-quick-command-reference.md -->
## Cross-Domain Query Guidance

When queries require data from multiple data products (e.g., Jira + Sales + Customer data):

1. **Follow Query Order:** Use `identify_dataproducts` output ordering ("first", "second", etc.)
2. **Query Dependencies:** Always query "first" data product, then use results to filter "second"
3. **Join Across Products:** Use common identifiers (customer_id, project_id, etc.)

**Example Flow:**
1. **First:** Get customer list from Customer data product
2. **Second:** Filter Jira issues for those customers only

---

## Visual Relationship Diagrams
