<!-- roverpeople · from 09-business-domain-knowledge.md -->
## 🎯 Quick Scenario Guide

| If user asks for... | Then use... | Key filters |
|-------------------|------------|------------|
| **"Who is [person]?" / "Find [person]"** | **`rover_people_curr` (profile lookup)** | **Return up to 10 matches. Split first/last name. No email guessing. See Rule #7.** |
| "Employee directory" | `rover_people_curr` | No filtering needed - data is pre-filtered |
| "Product team sizes" | `rover_alignment_curr` | Join with people table and split product_alignment |
| "Direct reports only" | `rover_people_curr` (self-join) | Simple join on manager_uuid = uuid. **Disambiguate person first (Rule #7).** |
| **"[Name]'s org" / span of control / direct+indirect reports** | **`rover_people_curr` (RECURSIVE CTE)** | **Same SQL for all phrasings (Rule #2b). Disambiguate person first (Rule #7).** |
| **"Cost center breakdown in [Manager]'s org"** | **`rover_people_curr` (RECURSIVE CTE → GROUP BY CC)** | **Recursive org tree first; never `cost_center IN (...)` without org walk** |
| **"How many in cost center 857?" (no manager named)** | `rover_people_curr` | `WHERE cost_center = '857'` or `cost_center IN (...)` |
| "Workforce analytics" (geo, department, no manager) | `rover_people_curr` | Group by geo, cost_center, employee_type |
| "Employee alignments" | `rover_alignment_curr` | Filter by specific alignment types |
| "Hiring trends" | `rover_people_curr` | Group by hire_date periods and analyze trends |

## 🔧 Data Quality Considerations

### Common Data Issues
- **Job Role Population**: Many job_role fields are NULL - use role_alignment for better coverage
- **Alignment Completeness**: Not all employees have alignment data - account for NULL values
- **Manager Hierarchy Integrity**: Validate against circular manager references in complex queries

## 💡 Advanced Analysis Patterns
