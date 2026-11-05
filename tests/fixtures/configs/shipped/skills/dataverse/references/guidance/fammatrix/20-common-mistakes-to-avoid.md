<!-- fammatrix · from 03-acronym-disambiguation.md -->
## ⚠️ COMMON MISTAKES TO AVOID

| ❌ WRONG | ✅ CORRECT | Why |
|----------|-----------|-----|
| `WHERE COSTCENTER = '871'` | `WHERE COSTCENTER = 'CC871'` | Always include "CC" prefix |
| BSO with multiple LIKE patterns | `WHERE DEPT_3 = 'BSO'` only | Keep filters simple and precise |
| Corporate with all 6 DEPT columns | Only DEPT_1, DEPT_2, DEPT_3 | Corporate uses 3 levels only |
| Finance managers with extra columns | Exactly 3 columns as specified | No extra columns beyond requirements |
| "Show all" with WHERE filters | NO WHERE clause | Don't filter "show all" queries |
| External reporting grouped by DEPT_1 | Just GROUP BY EXTERNAL_REPORTING | Never add department grouping |
| `WHERE UPPER(FAM_GLOBAL) LIKE '%EMEA%'` | Show ALL FAMs, not filtered | EMEA question means global view |
| Only checking CLT column | Check CLT OR CLT_1 OR CLT_2 | All three matter |
| Missing `#N/A%` exclusion | Add `NOT LIKE '#N/A%'` | Data quality requirement |

---
