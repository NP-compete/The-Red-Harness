<!-- roverpeople · from 02-critical-roverpeople-rules.md -->
### 6. **CEO & Executive Query Considerations** "Matt Hicks" is Redhat's CEO.
- **Self-Reporting**: CEOs and some executives have `manager_uuid = their own uuid`
- **Query Impact**: Without `e.uuid != e.manager_uuid`, CEOs appear as their own direct reports
- **Recursive CTEs**: Must use DISTINCT counting to prevent duplicate counting in hierarchies
- **Validation**: For CEOs, organizational totals should approach ~100% of company headcount
