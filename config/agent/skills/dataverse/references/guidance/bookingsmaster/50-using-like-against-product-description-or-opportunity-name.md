<!-- bookingsmaster · from 10-common-mistakes-to-avoid.md -->
### 9. ❌ Using LIKE Against Product Description or Opportunity Name

**Wrong** (using CONTAINS/LIKE on descriptions):
```sql
-- User asks: "What is ARR for RHEL?"
WHERE product_description ILIKE '%RHEL%'  -- Unreliable!
WHERE trx_name ILIKE '%Red Hat Enterprise Linux%'  -- Unreliable!
```

**Right**:
```sql
-- Use product_split_offering_group
WHERE product_split_offering_group = 'RHEL'  -- Reliable, standardized
```

**Product Field Hierarchy**:
1. `product_split_offering_group` - Primary (use this)
2. `product_split_offering_line` - Secondary
3. `product_split_offering_line_detail` - Tertiary
❌ NEVER use `product_description` or `trx_name` with LIKE

---
