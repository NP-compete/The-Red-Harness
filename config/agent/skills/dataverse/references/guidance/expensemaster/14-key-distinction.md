<!-- expensemaster · from 04-column-selection-guide-department-vs-acc-1.md -->
### Key Distinction

| Question Type | What You're Asking | GL_SUB_LEDGER_AGGREGATE Columns | ONESTREAM Table Columns |
|---------------|-------------------|--------------------------------|------------------------|
| **WHO/WHERE** | "What's the spend for GnA department?" | `cost_center_department`, `cost_center_hierarchy` | `cost_center_department`, `cost_center_hierarchy` |
| **WHAT** | "What's the spend on Software?" | `account_rollup`, `account_parent_cd`, `account_name` | `parent_account`, `account_hierarchy`, `account_name` |
