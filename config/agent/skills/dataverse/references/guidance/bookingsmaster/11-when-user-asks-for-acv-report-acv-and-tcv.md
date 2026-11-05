<!-- bookingsmaster · from 02-critical-business-rules-always-apply-1.md -->
### 6. When User Asks for "ACV", Report ACV+ and TCV

**MANDATORY RULE**: When users ask for "ACV", they mean **ACV+**. Always report `acv_plus_amount_usd_cy_pr` (ACV+) and `tcv_amount_usd_cy_pr` (TCV). Do **not** include `acv_amount_usd_cy_pr`.

```sql
SELECT
    SUM(acv_plus_amount_usd_cy_pr) as total_acv_plus_usd, -- ACV+ (includes consumption)
    SUM(tcv_amount_usd_cy_pr) as total_tcv_usd            -- TCV for context
```

**Metrics Hierarchy**:
- **ACV+** (`acv_plus_amount_usd_cy_pr`) - **Always use this** for ACV reporting, includes consumption
- **TCV** (`tcv_amount_usd_cy_pr`) - Total contract value, reported alongside ACV+

---
