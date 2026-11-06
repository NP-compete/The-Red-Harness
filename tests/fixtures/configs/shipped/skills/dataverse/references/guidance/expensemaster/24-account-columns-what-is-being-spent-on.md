<!-- expensemaster · from 06-column-selection-guide-department-vs-acc-3.md -->
### Account Columns (WHAT is being spent on)

Use these columns to filter by **expense type or category**:

**GL_SUB_LEDGER_AGGREGATE:**
- `account_rollup` - Highest level rollup category (e.g., "OpEx", "Compensation")
- `account_parent_cd` - Mid-level category with business logic (e.g., "Total Comp and Benefits", "T&E", "Software")
- `account_name` - Detailed expense type (e.g., "Computer Software Expense", "Travel Expense")

**ONESTREAM Tables:**
- `parent_account` - Parent/category level (highest, e.g., "Total Comp and Benefits")
- `account_hierarchy` - Full account hierarchy path
- `account_name` - Readable account name (most granular)

**Common Account Terms** (typically found in `account_name` and high-level account columns - GL: `account_rollup`, OneStream: `parent_account`):
- Expense types: Software, Travel, Hardware, Telecom, Rent, Utilities
- Service categories: Consulting, Professional Services, Maintenance, Support
- Terms ending in `Expense`: Computer Software Expense, Travel Expense, Marketing Expense
- Compensation terms: Wages, Salaries, Benefits, Bonus
- Cost categories: Total Comp and Benefits, Allocated Expenses
