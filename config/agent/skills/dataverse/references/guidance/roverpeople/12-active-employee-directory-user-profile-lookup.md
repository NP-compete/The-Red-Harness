<!-- roverpeople · from 04-essential-query-templates-1.md -->
### Active Employee Directory (User Profile Lookup)
```sql
-- Question: "Get user profile for mhicks" or "Show me information about Matt Hicks"
-- This query returns employee profile using TIERED matching:
--   Tier 0 = exact email or full name match → returned if any exist
--   Tier 1 = last name only fallback → returned ONLY if Tier 0 is empty
-- IMPORTANT: Always use table aliases to avoid column ambiguity in joins

WITH candidates AS (
    SELECT
        p.uuid,                    -- Unique identifier (GUID format)
        p.name,                    -- Full name (First + Last): e.g., "JOHN DOE", "AJ Smith"
        p.display_name,            -- First name or preferred name: e.g., "JOHN", "AJ"
        p.mail,                    -- Email address: e.g., "jdoe@redhat.com"
        p.job_role,                -- Role category: e.g., "Engineering", "PM" (can be null)
        p.title,                   -- Job title: e.g., "Associate Software Engineer"
        p.employee_type,           -- Employment type: "Employee" or "Contingent Worker"
        p.cost_center,             -- Cost center code: e.g., "878"
        p.cost_center_desc,        -- Department/Cost center: e.g., "R&D Ansible Engineering"
        p.geo,                     -- Geographic region: "NA", "APAC", "EMEA", "LATAM"
        p.hire_date,               -- Hire date timestamp (ISO 8601)
        p.manager_uuid,            -- Manager's UUID reference
        m.name as manager_name,    -- Manager's full name
        m.mail as manager_email,   -- Manager's email
        m.title as manager_title,  -- Manager's job title
        CASE
            WHEN p.mail ILIKE 'mhicks@redhat.com' THEN 0      -- Exact email (Tier 0)
            WHEN p.name ILIKE '%Matt%Hicks%' THEN 0            -- Full name (Tier 0)
            WHEN p.name ILIKE '%Hicks%Matt%' THEN 0            -- Reversed name (Tier 0)
            ELSE 1                                              -- Last name only (Tier 1)
        END AS match_tier
    FROM roverpeople_db.rhai_marts.rover_people_curr p
    LEFT JOIN roverpeople_db.rhai_marts.rover_people_curr m
        ON p.manager_uuid = m.uuid
    WHERE (
           p.mail ILIKE 'mhicks@redhat.com'       -- Exact kerberos (use @redhat.com, NOT prefix %)
           OR p.name ILIKE '%Matt%Hicks%'          -- Full name match
           OR p.name ILIKE '%Hicks%Matt%'          -- Reversed name order
           OR p.name ILIKE '%Hicks%'               -- Last name fallback (catches nicknames)
    )
)
SELECT uuid, name, display_name, mail, job_role, title, employee_type,
       cost_center, cost_center_desc, geo, hire_date, manager_uuid,
       manager_name, manager_email, manager_title
FROM candidates
WHERE match_tier = (SELECT MIN(match_tier) FROM candidates)
ORDER BY name
LIMIT 10;
```

**When user provides ONLY a name (no kerberos/email)** — do NOT guess email:
```sql
-- Question: "Do you know John Doe?" or "Looking for employee information about John Doe"
-- IMPORTANT: Do NOT fabricate email patterns from the name. Search by name fields only.
-- Tiered matching: exact name first, last-name fallback only if no exact match.

WITH candidates AS (
    SELECT
        p.uuid, p.name, p.display_name, p.mail, p.job_role, p.title,
        p.employee_type, p.cost_center, p.cost_center_desc, p.geo, p.hire_date,
        p.manager_uuid,
        m.name as manager_name, m.mail as manager_email, m.title as manager_title,
        CASE
            WHEN p.name ILIKE '%John%Doe%' THEN 0         -- Full name (Tier 0)
            WHEN p.name ILIKE '%Doe%John%' THEN 0         -- Reversed name (Tier 0)
            ELSE 1                                          -- Last name only (Tier 1)
        END AS match_tier
    FROM roverpeople_db.rhai_marts.rover_people_curr p
    LEFT JOIN roverpeople_db.rhai_marts.rover_people_curr m
        ON p.manager_uuid = m.uuid
    WHERE (
           p.name ILIKE '%John%Doe%'               -- Full name as provided
           OR p.name ILIKE '%Doe%John%'             -- Reversed order
           OR p.name ILIKE '%Doe%'                  -- Last name fallback (catches "Jonathan Doe")
    )
)
SELECT uuid, name, display_name, mail, job_role, title, employee_type,
       cost_center, cost_center_desc, geo, hire_date, manager_uuid,
       manager_name, manager_email, manager_title
FROM candidates
WHERE match_tier = (SELECT MIN(match_tier) FROM candidates)
ORDER BY name
LIMIT 10;

-- AGENT BEHAVIOR:
-- If 1 result  → Use it directly.
-- If 2+ results → Present all matches: "I found multiple people matching 'John Doe'. Which one did you mean?"
--                 Show: Name, Email, Title, Cost Center for each.
-- If 0 results  → Tell user: "I could not find anyone matching 'John Doe'. Please check the spelling or provide a kerberos ID/email."
```
