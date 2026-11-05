### **fammatrix (Finance Account Manger Matrix) (Finance Account Manager Matrix)**
**Database:** `fammatrix_db`
**Maturity:** AI Experimental

Cost center financial accountability system mapping financial ownership and departmental organizational structure.

**Primary use cases:** Cost center ownership, finance manager assignments, budget accountability, and departmental hierarchy mapping. Cost center ownership, Finance Manager and Finance Account Manager (FAM) assignments, budget accountability, and departmental hierarchy mapping provide key organizational context. This information informs Row-Level Security (RLS) and data access decisions for the ExpenseMaster Dataverse agent.

**When to route here:**
- Questions about cost center financial ownership or finance managers
- FAM (Finance Account Manger Matrix) (Finance Account Manager) assignments, budget owners, cost center owners
- Departmental organizational structure (Marketing, Sales and Services, Products and Global Engineering, Corporate Functions)
- Financial management responsibilities for cost centers

**🔑 KEY DISTINCTION:** fammatrix = financial accountability for cost centers | RoverPeople = employee data and reporting structure

**🔗 CROSS-DOMAIN QUERIES (fammatrix + RoverPeople):**
When a query asks about **people/employees within an organization or department**, use fammatrix FIRST to get the organizational structure and cost centers, then query RoverPeople for the employee data:
1. **Step 1:** Query fammatrix to identify cost centers under the specified organization (using DEPT_1 through DEPT_6 hierarchy)
2. **Step 2:** Query RoverPeople with those cost centers to get employee counts, names, or leadership

**Example Cross-Domain Questions (require BOTH products):**
- "How many associates work in the IT organization?" → fammatrix (IT cost centers) + RoverPeople (headcount)
- "Who is the leader of the IT organization?" → fammatrix (IT hierarchy) + RoverPeople (top manager)
- "Who runs Marketing?" / "Who leads Marketing?" → fammatrix (Marketing hierarchy) + RoverPeople (leadership)
- "List employees in Engineering department" → fammatrix (Engineering cost centers) + RoverPeople (employee list)

**Data Scope & Coverage:**

*What IS in fammatrix:*
- Cost center master list (618 unique cost centers with codes like CC975, CC871)
- 6-level departmental hierarchy (DEPT_1 through DEPT_6) for organizational structure
- Financial accountability assignments:
  - Finance managers (251 unique managers)
  - FAM (Finance Account Manger Matrix) (Finance Account Manager) global assignments
  - Budget owners (82 unique owners)
  - Cost center owners
  - CLT (Corporate Leadership Team) assignments (4 members)
- Department codes (CORP, Total_SnS, PnGE, MKT) and sub-departments
- HR support assignments (HRBP, Compensation Consultants)
- External reporting categories

*What IS NOT in fammatrix:*
- Individual employee information, headcount, or reporting relationships → Use **RoverPeople** (or cross-domain query)
- Actual financial transaction data or budget amounts → Use financial data products

**Example fammatrix-Only Questions:**
- "Who is the finance manager for cc871?"
- "How many cost centers are in Services organization?"
- "List departments under Marketing"
- "Show departmental hierarchy for Corporate Functions"
- "Which cost centers does [finance manager] financially manage?"

---

## Table guidance — two reads, found by search

`references/guidance/fammatrix/` holds 20 files, one rule or one
query template each, named for what it covers.

1. **`references/guidance/fammatrix/00-always-apply.md`** — the
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
