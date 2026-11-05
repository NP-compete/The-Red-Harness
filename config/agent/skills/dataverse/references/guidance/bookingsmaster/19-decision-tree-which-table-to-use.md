<!-- bookingsmaster · from 04-table-selection-guide.md -->
### Decision Tree: Which Table to Use?

```
Question about current or future quarter?
├─ YES → Use pipeline_transactions_acv
└─ NO → Historical/completed quarter?
           └─ YES → Use eoq_transaction_acv_snapshot
```

**Table Usage**:

| Table | When to Use | Key Characteristics |
|-------|-------------|---------------------|
| **pipeline_transactions_acv** | Current quarter ACV/TCV, open opportunities | Live data, most current |
| **eoq_transaction_acv_snapshot** | Historical quarters ACV/TCV, closed deals | Point-in-time, completed quarters |
| **pipeline_transactions_acv_snapshot** | Latest snapshot analysis | Requires `snapshot_date` filter, 695M+ records |
| **pipeline_transactions_arr** | Current quarter ARR (recurring revenue) | Use `revenue_recognition_date_fiscal_year_quarter` |
| **eoq_transaction_arr_snapshot** | Historical quarters ARR | Use `revenue_recognition_date_fiscal_year_quarter` |

---
