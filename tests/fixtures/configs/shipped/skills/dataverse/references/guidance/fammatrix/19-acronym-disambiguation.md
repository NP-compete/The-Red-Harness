<!-- fammatrix · from 03-acronym-disambiguation.md -->
## ⚠️ Acronym Disambiguation

Some acronyms match multiple cost centers. When ambiguous, search by `DESCRIPTION` using the full expanded term, not the acronym.

| Acronym | Common Confusion | Correct Search |
|---|---|---|
| SPO | Matches "O**SPO**" (CC708), "Re**spo**nse" (CC108), "S**po**nsorship" (CC506) | `DESCRIPTION ILIKE '%Strategy%Plan%Oper%'` for Strategy, Planning & Operations |
| OSPO | — | `DESCRIPTION ILIKE '%OSPO%'` for Open Source Program Office |

**Rule:** When user says "SPO" without "Open Source", search `DESCRIPTION ILIKE '%Strategy%Plan%Oper%'`. When user says "OSPO" or "Open Source", search `DESCRIPTION ILIKE '%OSPO%'`.

---

## 🚨 CRITICAL RULES

### ⚠️ COST CENTER FORMAT RULE
- **Always use the full format `CC###`** (e.g., `CC871`, `CC123`) - never just the number
- Cost centers in WHERE clauses must include the "CC" prefix: `WHERE COSTCENTER = 'CC871'`
- If user provides just digits (e.g., "871"), prepend "CC" automatically: `CC871`

### ⚠️ CRITICAL FILTER RULES
- **For BSO queries**: Use simple WHERE DEPT_3 = 'BSO' - NO extra OR conditions with LIKE
- **For department hierarchies**: Include ALL DEPT columns (DEPT_1 through DEPT_6) when showing full hierarchy
- **For specific cost centers**: Consider including key financial columns (FINANCE_MANAGER, FAM_GLOBAL, BUDGET_OWNER, CC_OWNER, CLT)

### Data Quality Filters
- **Always exclude `#N/A%` values** in FINANCE_MANAGER and FAM_GLOBAL columns
- **Use IS NOT NULL** for required fields
- **Don't add TRIM or complex string checks** unless necessary

### Query Simplicity
- **Avoid OVER() clauses** for percentages unless explicitly requested
- **Don't add ROUND() calculations** unless dealing with decimals
- **Keep ORDER BY simple** - usually just by count DESC or COSTCENTER
- **BSO queries**: Just use WHERE DEPT_3 = 'BSO', don't add LIKE patterns

### Result Management
- **Add LIMIT 20** for manager/personnel lists
- **Add LIMIT 50** for "show all" queries
- **Only use LISTAGG when showing specific items is valuable**

### Department Filtering
- **Use both LIKE and exact match**: `DEPT_1 LIKE '%Marketing%' OR DEPT_1 = 'MKT'`
- **Services = Total_SnS + RSS**: `WHERE DEPT_1 = 'Total_SnS' AND DEPT_2 = 'RSS'`
- **Include up to DEPT_3** for hierarchy queries, rarely need DEPT_4-6

---
