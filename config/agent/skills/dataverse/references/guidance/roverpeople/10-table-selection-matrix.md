<!-- roverpeople · from 03-table-selection-matrix.md -->
## 🎯 Table Selection Matrix

| Analysis Type | Primary Tables | Key Points |
|---------------|----------------|------------|
| **Employee Directory** | `rover_people_curr` | Basic employee information, contact details, and organizational data |
| **Complete Employee Profiles** | `rover_alignment_curr` | Full employee profiles including all alignment types |
| **Product Team Analysis** | `rover_people_curr` + `rover_alignment_curr` | Employee product assignments via alignment table |
| **Direct Reports Only** | `rover_people_curr` (self-joined) | Immediate manager-employee relationships |
| **⚠️ Span of Control / Manager Org Headcount** | `rover_people_curr` (RECURSIVE CTE) | **"Employees in [Name]'s org" = "reports to [Name] directly/indirectly" — same recursive CTE (Rule #2b)** |
| **⚠️ Manager Cost Center Breakdown** | `rover_people_curr` (RECURSIVE CTE) | **Recursive CTE first, then GROUP BY cost_center inside org tree — never `cost_center IN (...)` alone** |
| **Role-based Analysis** | `rover_people_curr` + `rover_alignment_curr` | Functional role assignments via alignment table |
