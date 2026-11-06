<!-- expensemaster · from 07-business-definitions-logic-gl-onestream.md -->
### Load Rate: Account Code Mapping

**CRITICAL**: For benefits load rate calculations, use **`account_code`** filters (not `account_name` or `account_hierarchy` ILIKE) so definitions are consistent and auditable.

**Account code reference** (use these exact codes in queries):

| ACCOUNT_CODE   | ACCOUNT_NAME              |
|----------------|---------------------------|
| COR_601000     | Wages                     |
| SGA_601000     | Wages                     |
| COR_601500     | Wages Vacation            |
| SGA_601500     | Wages Vacation            |
| COR_602000     | Employee Tax Expense      |
| SGA_602000     | Employee Tax Expense      |
| COR_604000     | Benefits                  |
| SGA_604000     | Benefits                  |
| COR_OthLoadRate| Other Load Rate Expense   |
| SGA_OthLoadRate| Other Load Rate Expense   |

- **Wages** (for load rate denominator): `account_code IN ('SGA_601000', 'COR_601000')`
- **Benefits** (for load rate numerator): `account_code IN ('SGA_602000', 'SGA_604000', 'SGA_601500', 'SGA_OthLoadRate', 'COR_602000', 'COR_604000', 'COR_601500', 'COR_OthLoadRate')`

**Benefits Load Rate = (Total Benefits / Total Wages) × 100**. Use `NULLIF(total_wages, 0)` to avoid division by zero.
