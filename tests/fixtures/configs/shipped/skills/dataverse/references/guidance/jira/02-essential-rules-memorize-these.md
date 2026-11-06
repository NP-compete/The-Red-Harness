<!-- jira · from 01-table-of-contents.md -->
### ⚡ Essential Rules (MEMORIZE THESE)

1. **Numeric IDs**: Issue types and statuses are NUMBERS, not strings
   ```sql
   -- ❌ WRONG: ji.issuetype = 'Epic'
   -- ✅ RIGHT: ji.issuetype = '10000'
   ```

2. **Status Categories**: Use universal categories instead of specific IDs
   ```sql
   WHERE js.statuscategory IN (2, 4)  -- "To Do" or "In Progress" (Open items)
   WHERE js.statuscategory = 3         -- "Done" (Completed items)
   ```

3. **Default Time Period**: When no time specified, use current quarter
   ```sql
   -- Priority 1: Fixed version (PI-CY25Q4)
   -- Priority 2: Date fallback (created/updated >= quarter_start)
   ```

4. **Project Joins**: Use `pkey` not `id`
   ```sql
   JOIN jira_project_rhai jp ON ji.project = jp.pkey  -- ✅ CORRECT
   ```

5. **Relationships**: Two different patterns
   - **Hierarchy** (parent-child): Use `jira_issuelink_rhai`
   - **Associations** (versions, components): Use `jira_nodeassociation_rhai`
