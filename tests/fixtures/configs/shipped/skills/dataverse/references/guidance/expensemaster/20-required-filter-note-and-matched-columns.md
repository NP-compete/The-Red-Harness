<!-- expensemaster · from 05-column-selection-guide-department-vs-acc-2.md -->
### ⚠️ REQUIRED: `_filter_note` and `matched_*` Columns

**Every query MUST include:**
1. `_filter_note` column as the FIRST column — **GL/OneStream:** describe filters applied (Rule #7). **Apptio spend:** use the fixed string from **Rule Apptio #8** only.
2. `matched_*` columns - show only the values that actually matched the search term (using CASE WHEN)

**REMINDER:** See **Critical Rule #7** ([Critical rules](#-critical-rules) → GL & OneStream): include `_filter_note` as the first column (with plan rate in the note) and state the plan rate in your natural-language response to the user. **Apptio spend:** **Critical Rule Apptio #8** — use only the standard one-line `_filter_note` (no filter list in that column).

**Format for `_filter_note`**: `'Filtered by: <column(s)> contains [<value(s)>]'` (GL/OneStream). **Apptio spend:** `'Using Apptio data, which includes spend that resides in IT cost centers.'`

**Examples (GL_SUB_LEDGER_AGGREGATE):**
- `'Filtered by: cost_center_department/cost_center_hierarchy contains [GnA]'`
- `'Filtered by: account_rollup/account_parent_cd/account_name contains [Software]'`
- `'Filtered by: cost_center_department/cost_center_hierarchy contains [PnGE] AND account_rollup/account_parent_cd/account_name contains [Travel]'`

**Examples (ONESTREAM tables):**
- `'Filtered by: cost_center_department/cost_center_hierarchy contains [GnA]'`
- `'Filtered by: parent_account/account_hierarchy/account_name contains [Software]'`
- `'Filtered by: cost_center_department/cost_center_hierarchy contains [PnGE] AND parent_account/account_hierarchy/account_name contains [Travel]'`

**Example (Apptio spend — ITPF and TBM):**
- `'Using Apptio data, which includes spend that resides in IT cost centers.'`

- `'Interpreted: <user_term> as <columns> contains [<interpreted_values>]'` (use when user term is abstract/conceptual and you expand it to related account terms)
