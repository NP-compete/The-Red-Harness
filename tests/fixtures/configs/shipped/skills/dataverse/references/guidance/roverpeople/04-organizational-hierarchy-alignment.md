<!-- roverpeople · from 02-critical-roverpeople-rules.md -->
### 2. **Organizational Hierarchy & Alignment**
- **Manager Relationships**: Complete manager hierarchy through `manager_uuid` self-joins
- **⚠️ SPAN OF CONTROL**: When asked for "span of control" analysis for a specific manager (e.g., "Alex Johnson"), **MUST use RECURSIVE CTE** to capture ALL direct and indirect reports throughout the entire reporting chain
- **⚠️ COST CENTER BREAKDOWN FOR MANAGERS**: When a user asks for a **cost center breakdown within** a manager's team (e.g., "show cost centers in Jane Smith's org"), **MUST use a recursive CTE first** to collect ALL direct + indirect reportees, **then** `GROUP BY cost_center` / `cost_center_desc` **inside that org tree**. Do **NOT** skip the recursive CTE and filter `rover_people_curr` by a static `cost_center IN (...)` list.
- **Direct Reports Only**: Simple self-joins sufficient for immediate direct reports
- **Product Alignment**: Employee assignments to Red Hat products (RHEL, OpenShift, Ansible, etc.)
- **Role Alignment**: Functional role assignments (Engineering, Marketing, Support, etc.)
