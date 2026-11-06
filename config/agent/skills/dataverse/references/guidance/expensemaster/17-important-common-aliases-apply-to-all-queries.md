<!-- expensemaster · from 04-column-selection-guide-department-vs-acc-1.md -->
### ⚠️ IMPORTANT: Common Aliases (Apply to ALL Queries)

**Before executing any query**, translate user terms to database values using this table:

| User May Say | Search For (Database Value) | Column Type | Column to Filter |
|--------------|----------------------------|-------------|------------------|
| G&A, GnA, General and Administrative, General & Administrative | `GnA` | Organizational | `cost_center_department`, `cost_center_hierarchy` |
| HR, Human Resources | See note below | Organizational | `cost_center_department`, `cost_center_hierarchy` |
| P&GE, PnGE, Products and Global Engineering | See note below | Organizational | `cost_center_department`, `cost_center_hierarchy` |
| TAM, Technical Account Management | See note below | Organizational | `cost_center_department` (exact match preferred) |

**HR/Human Resources/PPL Special Case:**

| User Says | Filter To Use |
|-----------|---------------|
| "HR", "Human Resources", "People" | `WHERE cost_center_department = 'People'` (exact match) |
| "PPL", "PPL team", "PPL org" | `WHERE (cost_center_department = 'People' OR REGEXP_LIKE(cost_center_hierarchy, '(^|.*[|])PPL[_|].*'))` |

```sql
-- When user says "HR", "Human Resources", or "People" → use exact match:
WHERE cost_center_department = 'People'

-- When user says "PPL" explicitly → ALWAYS include hierarchy REGEXP:
WHERE (cost_center_department = 'People'
       OR REGEXP_LIKE(cost_center_hierarchy, '(^|.*[|])(People|PPL)[_|].*'))
```

**CRITICAL - PPL Trigger Words:**
If the user's question contains ANY of these terms: **"PPL"**, **"PPL org"**, **"PPL team"**, **"for PPL"**, **"the PPL"** → you MUST include the REGEXP pattern. Do NOT translate "PPL" to just "People" department.

- There is NO department called "PPL" in the data. The department is called `'People'`.
- "PPL" appears only in `cost_center_hierarchy` values (e.g., `PPL_RH`, `PPL_IBM`, `PPL_IBM_RH`).
- **WRONG:** `cost_center_department = 'People'` alone when user says "PPL" ← Misses PPL hierarchies
- **WRONG:** `cost_center_department = 'PPL'` ← Returns NO results
- **CORRECT:** `(cost_center_department = 'People' OR REGEXP_LIKE(cost_center_hierarchy, '(^|.*[|])PPL[_|].*'))`

**PnGE (Products and Global Engineering) Special Case:**

| User Says | Filter To Use |
|-----------|---------------|
| "PnGE", "P&GE", "Products and Global Engineering" | `WHERE cost_center_department IN ('Products', 'Global Engineering')` |
| "PnGE Engineering", "Global Engineering within PnGE" | `WHERE cost_center_department = 'Global Engineering'` (Pattern A — Known Department) |
| "PnGE Products", "Products within PnGE" | `WHERE cost_center_department = 'Products'` (Pattern A — Known Department) |

```sql
-- When user asks for the full PnGE org → filter both Known Departments:
WHERE cost_center_department IN ('Products', 'Global Engineering')

-- Equivalent (PnGE is the top-level hierarchy segment):
WHERE cost_center_hierarchy LIKE 'PnGE|%'
-- Or use the standard hierarchy REGEXP (term at start of path):
WHERE REGEXP_LIKE(cost_center_hierarchy, '(^|.*[|])PnGE[_|].*')

-- When user asks for one arm only → use Pattern A on that department:
WHERE cost_center_department = 'Global Engineering'  -- engineering/R&D spend
WHERE cost_center_department = 'Products'            -- product BU spend
```

- There is NO department called `'PnGE'` in the data. `cost_center_department = 'PnGE'` returns **no rows**.
- PnGE is an organizational umbrella spanning two **Known Departments**: `'Products'` and `'Global Engineering'`.
- `PnGE` appears as the **first segment** of `cost_center_hierarchy` (e.g., `PnGE|Global_Engineering|...`, `PnGE|Products|Hybrid_Platforms_BU|`), not as a mid-hierarchy token.
- **WRONG:** `cost_center_department = 'PnGE'` ← Returns NO results
- **WRONG:** `REGEXP_LIKE(cost_center_hierarchy, '.*[|]PnGE[_|].*')` ← Returns NO results (old pattern misses terms at the start of the hierarchy)
- **CORRECT (full PnGE org):** `cost_center_department IN ('Products', 'Global Engineering')`

**TAM Special Case:**
```sql
-- TAM is a department. Use exact match on cost_center_department:
SELECT
    'Filtered by: cost_center_department = TAM' as _filter_note,
    'cost_center_department: TAM' as matched_at,  -- Static value since exact match
    account_rollup,
    SUM(amount_usd) as total_spend
FROM EXPENSEMASTER_DB.RHAI_MARTS.GL_SUB_LEDGER_AGGREGATE
WHERE cost_center_department = 'TAM'
GROUP BY account_rollup
ORDER BY total_spend DESC;
-- Note: 'LATAM' (Latin America) exists in hierarchies like 'Field_Marketing_LATAM' - using exact match on cost_center_department avoids this
```

| IT, Information Technology | `IT` | Organizational | Use word-boundary matching (see Hierarchy Matching Rule) |
| T&E, Travel & Entertainment | `Travel and Entertainment` | Account | GL: `account_rollup`, OneStream: `pare
