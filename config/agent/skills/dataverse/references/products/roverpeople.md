### **RoverPeople**
**Database:** `roverpeople_db`

Red Hat's internal corporate directory containing active employees, contractors, and employee-based organizational hierarchy information.

Provides complete workforce analytics including product alignments, manager relationships, cost center assignments, and geographic distribution.

**Primary use cases:** Org chart analysis, headcount reporting, team composition planning, and employee alignment tracking across business units.

**When to route here:** Queries about employees, managers, organizational structure, reporting hierarchies, headcount, team composition, or workforce demographics.

**Data Scope & Coverage:**

*What IS in RoverPeople:*
- Active employees and contingent workers (contractors, consultants)
- Terminated/former employees with historical data for audit purposes
- Employee profile information (name, email, title, job role, employee type)
- Organizational hierarchy and manager relationships (complete self-referential structure)
- Manager span of control (direct and indirect reports)
- Cost center information and department assignments
- Geographic distribution (regions: NA, EMEA, APAC, LATAM)
- Product alignments for tax credit and R&D tracking
- Role alignments for functional classification
- Project alignments for development initiatives
- Subproduct alignments for granular product categorization
- Employee lifecycle data (hire dates, original hire dates, termination dates)
- Daily data synchronization from Aurora PostgreSQL via Fivetran

**🔑 ROUTING DECISION:**
- **Employee data** (who works where, reporting structure, team composition) → **RoverPeople**
- **Financial accountability** (cost center ownership, finance managers, FAM assignments) → **fammatrix**
- **Organizational Hierarchy** (cost center levels and organization structure) → **fammatrix**
- **Organization-level people queries** (headcount/employees in a department or org) → **fammatrix FIRST, then RoverPeople** (see cross-domain section below)

**🔗 CROSS-DOMAIN QUERIES (fammatrix + RoverPeople):**
For questions combining organizational hierarchy with people data, use a **two-step approach**:
1. **Step 1:** Query **fammatrix** to identify cost centers within the specified organization/department
2. **Step 2:** Query **RoverPeople** to get employee data for those cost centers

**Example Cross-Domain Questions:**
- "How many associates work in the IT organization?" → Query fammatrix for IT cost centers, then RoverPeople to count employees
- "Who is the leader of the IT organization?" → Query fammatrix for IT hierarchy, then RoverPeople for leadership
- "Who runs Marketing?" / "Who leads Marketing?" → Query fammatrix for Marketing hierarchy, then RoverPeople for leadership
- "List all employees in the Engineering department" → Query fammatrix for Engineering cost centers, then RoverPeople for employee list

**Example RoverPeople-Only Questions:**
1. "Who is Marco Bill?" (employee profile)
2. "Who reports to Carl Trieloff?" (direct reports)
3. "Show Marco Bill's organizational structure" (span of control)
4. "How many employees work in cost center 857?" (headcount - cost center already known)
5. "Which cost centers do Marco Bill's team members work in?" (team distribution)

---

## Table guidance — two reads, found by search

`references/guidance/roverpeople/` holds 29 files, one rule or one
query template each, named for what it covers.

1. **`references/guidance/roverpeople/00-always-apply.md`** — the
   filters and exclusions that apply to every query against this
   product. Skipping it is how a statement runs clean and returns
   the wrong number.
2. **`grep` the directory for the business term, column or metric
   in the question** — "closed booking flag", "cost center
   hierarchy", "ACV_PLUS", "variance" — then read the one or two
   files that match. `glob` it instead if you would rather scan
   the names.

Never read the directory through. The query templates are working
SQL carrying the business filters that make the numbers correct;
adapt the closest one rather than writing fresh.
