<!-- sfsaleslegacy · from 05-universal-architectural-patterns-best-pr.md -->
### Universal Filtering Pattern
Almost every view in this database requires a standard set of filters. You must include these in your queries unless explicitly told otherwise.
```sql
WHERE is_deleted = 0
AND _fivetran_active = 1
```

* `is_deleted = 0`: Excludes records that have been soft-deleted in the source Salesforce system.
* `_fivetran_active = 1`: A Fivetran metadata flag that ensures the record is part of the current, active dataset.
* **Exceptions**: A few specialized views in PSA_MARTS (e.g., psa_pse_timecard, psa_pse_milestone) intentionally omit `_fivetran_active = 1` to preserve a complete historical audit trail.
