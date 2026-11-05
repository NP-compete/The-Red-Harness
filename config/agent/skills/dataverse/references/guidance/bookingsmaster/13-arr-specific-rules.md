<!-- bookingsmaster · from 02-critical-business-rules-always-apply-1.md -->
### 8. ARR-Specific Rules

**CRITICAL**: ARR queries require different tables, columns, and filters than ACV queries.

**ARR Tables**:
- `pipeline_transactions_arr` - Current/future quarter ARR
- `eoq_transaction_arr_snapshot` - Historical quarter ARR

**⚠️ CRITICAL: Column Name Differences Between ARR Tables**

Sales group and company columns have **different names** by table. Using the wrong name causes SQL compilation errors (e.g. `invalid identifier 'EOQ_TRANSACTION_ARR_SNAPSHOT.SALES_GROUP_NAME'`) or inflated totals.

| Use case        | PIPELINE_TRANSACTIONS_ARR   | EOQ_TRANSACTION_ARR_SNAPSHOT      |
|-----------------|-----------------------------|-----------------------------------|
| Sales group     | `SALES_GROUP_NAME`          | `ACCOUNT_SALES_GROUP_NAME`        |
| Company/global  | `GLOBAL_SALES_GROUP_NAME`   | `ACCOUNT_GLOBAL_SALES_GROUP_NAME` |

**Template for ARR
