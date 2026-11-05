<!-- expensemaster · from 05-column-selection-guide-department-vs-acc-2.md -->
### ⚠️ Choosing Between Organizational vs Account Hierarchy

This is the **most critical decision** for generating correct queries. The same term (e.g., "Marketing") has completely different meanings depending on context.

**The Core Question:**
- **ORGANIZATIONAL hierarchy** = "**WHO** is spending?" → Use `cost_center_department`, `cost_center_hierarchy` columns (same for both tables)
- **ACCOUNT hierarchy** = "**WHAT** is being spent on?" → Use:
  - **GL_SUB_LEDGER_AGGREGATE**: `account_rollup`, `account_parent_cd`, `account_name`
  - **ONESTREAM tables**: `parent_account`, `account_hierarchy`, `account_name`

**How to Determine:**

| User Intent | Hierarchy | Example Questions |
|-------------|-----------|-------------------|
| Asking about a **team/department/org unit** | ORGANIZATIONAL | "What did Marketing department spend?", "Engineering org expenses", "GnA cost center breakdown" |
| Asking about an **expense type/category** | ACCOUNT | "What are Marketing expenses?", "Show Software spend", "T&E costs by vendor" |
| Asking about **expense type within a team** | BOTH | "What did Engineering spend on Software?" |

**Ambiguous Terms:**
Some terms exist in BOTH hierarchies (e.g., "Marketing" is both a department AND an expense type "Marketing Expense"). When ambiguous:
1. Look for context clues in the question: "department", "org", "team" → ORGANIZATIONAL; "expenses", "costs" → ACCOUNT
2. If truly ambiguous with no context, **default to ACCOUNT** (expense type)
