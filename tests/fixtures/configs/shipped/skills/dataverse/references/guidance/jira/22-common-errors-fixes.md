<!-- jira · from 02-4-advanced-patterns.md -->
### ❌ Common Errors & Fixes

#### Error: "No results returned"
**Check:**
1. Project key exists: `SELECT pkey FROM jira_db.cloudrhai_marts.jira_project_rhai WHERE pkey = 'KEY'`
2. Issue type ID is correct (use numeric ID, not name)
3. Status category filter isn't too restrictive
4. Version name exists in the project

#### Error: "Column not found"
**Check:**
1. Using correct schema: `jira_db.cloudrhai_marts`
2. Table alias matches: `ji` for issues, `jp` for projects, etc.
3. Join conditions are complete

#### Error: "Data type mismatch"
**Check:**
1. Issue types/statuses as strings: `ji.issuetype = '16'` (not `16`)
2. Sprint ID casting: `CAST(cfv.stringvalue AS INTEGER)`
3. Date conversions: `TO_TIMESTAMP(sprint_date/1000)`
