<!-- roverpeople · the rules that apply to every query here -->
# Always apply — roverpeople

Read this before writing any SQL for this product. Everything
below applies regardless of what the question asks.

## 🔴 Critical RoverPeople Rules

### 1. **Employee Lifecycle Management**
- **Active Status**: Data in RHAI_MARTS is pre-filtered to include only active employees - no additional filtering needed
- **Employee Types**: Distinguish between full-time employees and contingent workers
- **Hire Tracking**: Use `hire_date` for tenure and hiring analysis

### 2b. **⚠️ Manager "Org" Queries vs Cost Center Queries (CRITICAL — Same SQL)**

When a question names a **person/manager** and asks about their **org**, **team**, or **headcount**, it means **reporting hierarchy** (who reports to them via `manager_uuid`), **NOT** cost center membership.

**These phrasings are equivalent — use the SAME recursive CTE span-of-control query:**

| User phrasing (examples) | Correct approach |
|--------------------------|------------------|
| "How many employees are in **Itamar Heim's org**?" | Recursive CTE downward from manager |
| "How many employees report to **Itamar Heim** directly and indirectly?" | Same recursive CTE |
| "What is **Jane Smith's** span of control?" | Same recursive CTE |
| "How big is **Carl Trieloff's** organization?" | Same recursive CTE |
| "Headcount under **Alex Johnson**" | Same recursive CTE |
| "Total reports for **[Manager Name]**" | Same recursive CTE |

**Routing rule:** If the question contains **a person's name** + any of `{org, organization, team, reports, span of control, headcount, how many employees}` → **ALWAYS** resolve the manager (Rule #7 tiered matching), then walk **down** with a recursive CTE. Return `direct_reports`, `indirect_reports`, and `total_reports` (or equivalent).

**❌ WRONG — do NOT generate this for manager org questions:**

```sql
-- WRONG: cost center aggregation is NOT a manager's org
SELECT cost_center, cost_center_desc, COUNT(*) AS employee_count
FROM roverpeople_db.rhai_marts.rover_people_curr
WHERE cost_center IN ('672', '677', '701', '707', '714')  -- never infer CC list from manager profile
GROUP BY cost_center, cost_center_desc;
```

**Why this fails:** Cost centers are a **finance/HR dimension**. A manager's org is everyone in their **reporting chain**, regardless of cost center. People in the manager's org may span many cost centers; people in one cost center may not report to that manager.

**✅ CORRECT — manager org headcount (concise template):**

```sql
-- Questions: "How many employees are in [Manager Name]'s org?"
--           "How many employees report to [Manager Name] directly and indirectly?"
-- Same SQL for both — disambiguate manager first (Rule #7), then recursive downward walk.
WITH base_manager AS (
    SELECT uuid, name, mail
    FROM roverpeople_db.rhai_marts.rover_people_curr
    WHERE (
        name ILIKE '%FirstName%LastName%'       -- e.g., '%Itamar%Heim%'
        OR name ILIKE '%LastName%'               -- last name fallback — e.g., '%Heim%'
    )
    QUALIFY ROW_NUMBER() OVER (
        ORDER BY CASE WHEN name ILIKE '%FirstName%LastName%' THEN 0 ELSE 1 END, uuid
    ) = 1
),
org_tree AS (
    SELECT p.uuid, p.employee_type, 0 AS level, CAST(p.uuid AS VARCHAR) AS path
    FROM roverpeople_db.rhai_marts.rover_people_curr p
    JOIN base_manager b ON p.uuid = b.uuid
    UNION ALL
    SELECT e.uuid, e.employee_type, t.level + 1, t.path || '>' || e.uuid
    FROM org_tree t
    JOIN roverpeople_db.rhai_marts.rover_people_curr e ON e.manager_uuid = t.uuid
    WHERE e.uuid != e.manager_uuid
      AND t.level < 8
      AND t.path NOT LIKE '%' || e.uuid || '%'
)
SELECT
    (SELECT name FROM base_manager) AS manager_name,
    COUNT(DISTINCT CASE WHEN level = 1 THEN uuid END) AS direct_reports,
    COUNT(DISTINCT CASE WHEN level > 1 THEN uuid END) AS indirect_reports,
    COUNT(DISTINCT CASE WHEN level > 0 THEN uuid END) AS total_reports,
    COUNT(DISTINCT CASE WHEN level > 0 AND employee_type = 'Employee' THEN uuid END) AS employees,
    COUNT(DISTINCT CASE WHEN level > 0 AND employee_type = 'Contingent Worker' THEN uuid END) AS contractors
FROM org_tree;
```

**Use cost center `GROUP BY` only when the user asks about cost centers explicitly**, e.g. "How many people in cost center 857?" or "Headcount by cost center in EMEA" — **without** tying the question to a named manager's org.

### 3. **Geographic & Location Management**
- **Regional Distribution**: Use `geo` field for regional analysis (NA, EMEA, APAC, LATAM)
- **Country Data**: The `COUNTRY` column is **entirely NULL** — do NOT use it. For country-level analysis, use `CO` which contains ISO 3-letter country codes (e.g., "USA", "IND", "CZE", "GBR") and is 100% populated. For regional aggregation, prefer `GEO`.

### 4. **Data Structure & Integration**
- **PostgreSQL Source**: Direct Aurora PostgreSQL database connection via Fivetran
- **Daily Sync**: Daily data synchronization at 1:00 AM UTC
- **UUID-based**: Primary identifiers use UUID format for cross-system integration

### 6b. **⚠️ Bi-Directional Org Traversal (CRITICAL — Snowflake Limitation)**
- **NEVER put both upward (to CEO) and downward (to reports) traversal in a single recursive CTE.** Snowflake rejects this with `invalid Recursive CTE` because it cannot prove termination for bi-directional self-joins.
- **When a query asks for BOTH the reporting chain upward AND all direct/indirect reports downward**, you **MUST split into two separate recursive CTEs** inside one `WITH RECURSIVE` block:
  1. `upward_chain` — walks **up** via `manager_uuid` (depth decrements: 0, -1, -2, … to CEO)
  2. `downward_reports` — walks **down** via `manager_uuid` (depth increments: 0, 1, 2, … to leaf employees)
- Then `UNION ALL` the results, deduplicating the target employee (depth = 0) which appears in both CTEs.
- See the **"Bi-Directional Org Traversal"** template in the Essential Query Templates section below.

### 7. **⚠️ Employee Lookup & Disambiguation (CRITICAL)**

**NEVER silently pick one result. NEVER guess email addresses. ALWAYS present options when ambiguous.**

This rule applies to ALL employee profile lookups, direct report lookups, management chain queries, and any query that starts by finding a specific person.

#### A. Tiered Name Matching — Exact First, Fallback Only When Needed
When the user provides a person's name (e.g., "John Doe"), the SQL **MUST** use a **tiered matching** approach:

- **Tier 0 (exact):** Full name match (`%John%Doe%`), reversed name (`%Doe%John%`), or exact email match
- **Tier 1 (fallback):** Last name only (`%Doe%`) — catches nicknames like John → Jonathan, Bill → William

**CRITICAL: Only show Tier 1 (fallback) results if there are ZERO Tier 0 (exact) matches.** If "Carl Trieloff" matches exactly, do NOT also show "Sarah Trieloff" from the last-name fallback.

Use a `match_tier` CTE to implement this:

```sql
-- Tiered matching pattern:
WITH candidates AS (
    SELECT
        p.*,
        m.name as manager_name, m.mail as manager_email, m.title as manager_title,
        CASE
            WHEN p.mail ILIKE 'kerberos@redhat.com' THEN 0     -- Exact email (Tier 0)
            WHEN p.name ILIKE '%FirstName%LastName%' THEN 0     -- Full name (Tier 0)
            WHEN p.name ILIKE '%LastName%FirstName%' THEN 0     -- Reversed name (Tier 0)
            ELSE 1                                               -- Last name only (Tier 1 — fallback)
        END AS match_tier
    FROM roverpeople_db.rhai_marts.rover_people_curr p
    LEFT JOIN roverpeople_db.rhai_marts.rover_people_curr m ON p.manager_uuid = m.uuid
    WHERE (
        p.mail ILIKE 'kerberos@redhat.com'
        OR p.name ILIKE '%FirstName%LastName%'
        OR p.name ILIKE '%LastName%FirstName%'
        OR p.name ILIKE '%LastName%'
    )
)
SELECT * FROM candidates
WHERE match_tier = (SELECT MIN(match_tier) FROM candidates)   -- Only best tier
ORDER BY name
LIMIT 10;
```

#### B. Email/Kerberos Matching — Exact Domain Only, Never Guess
- Use `p.mail ILIKE 'rjones@redhat.com'` (with `@redhat.com`), **NOT** `'rjones%'` — prefix match causes collisions (e.g., "rjones" matching "rjoneson").
- **Only use email matching when the user explicitly provides a kerberos ID or email.** Do NOT fabricate email patterns like `mikeferris@redhat.com` or `mferris@redhat.com` from a person's name — these guesses are unreliable and produce inconsistent results across sessions.

#### C. Agent Behavior After Query Returns Results

| Result Count | Agent Behavior |
|---|---|
| **Exactly 1 match** | Use the result directly and answer the user's question. |
| **2–10 matches** | Present ALL matches as a numbered list (Name, Email, Title, Cost Center). Ask: *"I found multiple people matching your query. Which one did you mean?"* |
| **0 matches** | Inform the user: *"I could not find anyone matching '[name]'. Please verify the spelling or try a kerberos ID/email."* |
