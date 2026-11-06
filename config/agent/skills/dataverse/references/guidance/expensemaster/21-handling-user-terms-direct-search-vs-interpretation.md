<!-- expensemaster · from 05-column-selection-guide-department-vs-acc-2.md -->
### Handling User Terms: Direct Search vs Interpretation

When a user asks about an expense type, determine if the term is **concrete** or **abstract**:

| Term Type | Description | Action |
|-----------|-------------|--------|
| **Concrete** | Specific, likely exists in account data | Search directly using ILIKE |
| **Abstract** | Conceptual, unlikely to exist verbatim in account columns | Interpret into related account terms based on your understanding of expense categories |

**For abstract terms:**
1. Think about what account categories would logically contain this type of expense
2. Expand to multiple related search terms using OR conditions
3. Use "Interpreted:" prefix in `_filter_note` to show the user what terms you searched for
