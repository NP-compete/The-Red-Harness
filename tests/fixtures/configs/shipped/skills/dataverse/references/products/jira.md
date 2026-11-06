### **JIRA**
**Database:** `jira_db`

Atlassian JIRA data providing project management analytics, issue tracking, and development workflow insights.

Tracks project progress, issue resolution, team productivity, and development cycle analytics.

**Primary use cases:** Project performance analysis, development productivity measurement, issue resolution tracking, and agile workflow optimization.

**When to route here:** Queries about project management, issue tracking, sprint analytics, development workflows, bug tracking, or team productivity in engineering/IT projects.

**Data Scope & Coverage:**

*What IS in JIRA:*
- Issue tracking data (issues, tasks, bugs, epics) with PII-filtered views
- Project metadata (150+ projects) and configurations
- Sprint data with dates, status, and team assignments
- Issue statuses and workflows with status categories (To Do, In Progress, Done)
- Custom fields including Story Points and Sprint associations
- Components, versions, and fix versions for releases
- User data and team assignments (opportunity team members)
- Issue relationships via nodeassociation pattern (parent-child, dependencies)
- Velocity metrics and agile workflow analytics
- Historical sprint data for trend analysis

---

## Table guidance — two reads, found by search

`references/guidance/jira/` holds 45 files, one rule or one
query template each, named for what it covers.

1. **`references/guidance/jira/00-always-apply.md`** — the
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
