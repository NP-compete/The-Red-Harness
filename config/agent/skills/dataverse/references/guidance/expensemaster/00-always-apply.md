<!-- expensemaster · the rules that apply to every query here -->
# Always apply — expensemaster

Read this before writing any SQL for this product. Everything
below applies regardless of what the question asks.

## 🔴 Critical rules

Apply the **Common** rules for all sources; then apply the subsection for your chosen data source (**GL & OneStream**, **Apptio**, or **Cloudability**).

### ⚠️ CRITICAL: Hierarchy Matching Rule (Avoid False Positives)

The `cost_center_hierarchy` column is **pipe-delimited** (e.g., `CORP|GnA_RH|IT_RH|Security_RH`). Segments can have multiple underscores (e.g., `Product_And_Product_Engineering`). **Never use bare `%<term>%`** which matches substrings within segment names.

**Always use word-boundary matching:**

The hierarchy format is: `CORP|GnA_RH|IT_RH|Security_RH|` (segments separated by `|`, words within segments separated by `_`)

**Known Departments** (use exact match on `cost_center_department` when the search term matches one of these):
- Legal and Business Affairs
- TAM
- People
- Sales
- Finance
- Board and Executive
- Services
- Facilities
- Global Engineering
- Corporate Projects
- Operations
- Project Sunshine
- Marketing Department
- Procurement
- Products

**Matching Rule (CHOOSE ONE - do not combine):**

Before generating the query, check if the search term matches a known department above:

| If Search Term... | Then Use | Example |
|-------------------|----------|---------|
| **Matches a known department** (e.g., Services, Sales, Finance) | `WHERE cost_center_department = '<term>'` | `WHERE cost_center_department = 'Services'` |
| **Does NOT match a known department** (e.g., IT, GnA, Engineering) | Word-boundary matching on hierarchy | See pattern below |

```sql
-- ❌ WRONG: Bare ILIKE matches substrings (false positives)
WHERE cost_center_hierarchy ILIKE '%IT%'   -- Matches Benefits, Facilities, Digital, etc.

-- ❌ WRONG: Using underscore ILIKE patterns causes false positives
WHERE cost_center_hierarchy ILIKE '%_IT_%'  -- Matches Dig_IT_al in "Digital"

-- ✅ PATTERN A: Search term IS a known department (use this pattern)
WHERE cost_center_department = '<term>'

-- ✅ PATTERN B: Search term is NOT a known department (use REGEXP for word-boundary matching)
WHERE (cost_center_department = '<term>'
       OR REGEXP_LIKE(cost_center_hierarchy, '(^|.*[|])(<term>)[_|].*'))
```

**REGEXP Pattern Explained:**
- `(^|.*[|])` — Match **start of string** OR any characters followed by a pipe delimiter (handles terms at the beginning of the hierarchy, e.g. `PnGE|...`, as well as mid-path segments like `|IT_RH|`)
- `<term>` — The search term (e.g., IT, GnA, PPL, PnGE)
- `[_|]` — Match underscore OR pipe (word boundary after term)
- `.*` — Match any characters after

**⚠️ Multi-Org Queries:** When filtering by multiple orgs, check EACH org against Known Departments list above. **Do NOT use `IN (...)` blindly.**

| Org in Query | Is Known? | Filter to Use |
|--------------|-----------|---------------|
| Sales | ✅ Yes | `cost_center_department = 'Sales'` |
| RSS | ❌ No | `cost_center_department = 'RSS' OR REGEXP_LIKE(...)` |

**Combined multi-org filter:**
```sql
-- Sales is Known, RSS is NOT Known → combine patterns
WHERE (cost_center_department = 'Sales'
       OR cost_center_department = 'RSS'
       OR REGEXP_LIKE(cost_center_hierarchy, '(^|.*[|])RSS[_|].*'))

-- ❌ WRONG: Do not use IN() when any org is NOT a Known Department
WHERE cost_center_department IN ('Sales', 'RSS')  -- Misses RSS hierarchy matches!
```

**Why REGEXP works:**
| Search | Hierarchy Value | ILIKE `%IT%` | REGEXP | Why |
|--------|-----------------|--------------|--------|-----|
| IT | `\|IT_RH\|` | ✅ | ✅ | `|IT_` matches pattern |
| IT | `\|Digital_Experience\|` | ✅ ❌ | ❌ | No `|IT_` or `|IT|` in string |
| IT | `\|Benefits_RH\|` | ✅ ❌ | ❌ | No `|IT_` or `|IT|` in string |
| IT | `\|Enterprise_IT\|` | ✅ | ✅ | `|IT|` matches `(^|.*[|])IT[_|]` |
| PnGE | `PnGE\|Global_Engineering\|...` | ✅ ❌ | ✅ | `(^|...)` matches term at **start** of hierarchy |
| Applications | `\|Enterprise_Applications_RH\|` | ✅ | ✅ | `|Applications_` matches pattern |

**Key principle:** Use REGEXP to match search terms at the **start of the hierarchy** or after `|`, followed by `_` or `|`.

**Apply this rule to ALL organizational queries** - not just special cases like IT.
