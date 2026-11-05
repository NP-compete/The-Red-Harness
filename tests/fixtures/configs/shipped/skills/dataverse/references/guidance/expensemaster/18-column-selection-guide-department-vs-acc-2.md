<!-- expensemaster · from 05-column-selection-guide-department-vs-acc-2.md -->
nt_account` |
| Misc OpEx, Miscellaneous OpEx, Misc Operating Expense | `Miscellaneous Operating Expense` | Account | GL: `account_rollup`, OneStream: `parent_account` |

> **Rule**: Always apply these translations before searching. Use the specified column for filtering.

**Vendor Name Expansion (REQUIRED):**
When searching by `vendor_customer`, ALWAYS search for both the abbreviation AND the full company name using OR:
```sql
-- REQUIRED: Always expand vendor abbreviations to include full names
WHERE (vendor_customer ILIKE '%<abbreviation>%' OR vendor_customer ILIKE '%<full_company_name>%')
```

**Department Name Expansion (REQUIRED):**
When searching by `cost_center_department`, ALWAYS search for both the abbreviation AND the full department name using OR:
```sql
-- REQUIRED: Always expand department abbreviations to include full names
WHERE (cost_center_department ILIKE '%<abbreviation>%' OR cost_center_department ILIKE '%<full_department_name>%')
```
