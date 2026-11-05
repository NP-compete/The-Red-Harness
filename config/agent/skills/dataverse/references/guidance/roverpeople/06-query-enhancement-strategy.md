<!-- roverpeople · from 02-critical-roverpeople-rules.md -->
### 5. **Query Enhancement Strategy**
- **Always Include Analytics**: Even simple requests like "Get direct reports" should return comprehensive analytics
- **Anticipate Follow-ups**: Include data that answers likely follow-up questions
- **Business Context**: Add percentages, comparisons, and trends to raw numbers
- **Structured Output**: Use consistent sections for easy interpretation
- **SQL Best Practices**:
  - ALWAYS use table aliases (p for people, m for manager, e for employee, a for alignment)
  - Prefix ALL columns with their table alias to prevent ambiguity errors
  - Use meaningful aliases that match the table purpose
  - **Cost Center Queries**: Always use `IN` instead of `BETWEEN` for cost center filtering to avoid picking up unintended cost centers (e.g., use `cost_center IN ('491', '492', '493')` not `cost_center BETWEEN '491' AND '493'`)
