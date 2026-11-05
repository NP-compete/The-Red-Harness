<!-- bookingsmaster · from 09-key-column-reference-guide.md -->
### How to Choose the Right Table

```
1. Is the question about TARGETS, MJ, or FORECASTING?
   └─ YES → Use FORECASTING data product, NOT Bookingsmaster

2. Is the question about CURRENT or FUTURE quarter?
   └─ YES → Use pipeline_transactions_acv

3. Is the question about HISTORICAL/COMPLETED quarter?
   └─ YES → Use eoq_transaction_acv_snapshot

4. Do you need LATEST SNAPSHOT for a specific point-in-time?
   └─ YES → Use pipeline_transactions_acv_snapshot
            CRITICAL: MUST filter by snapshot_date (695M+ records!)
```

---

## ⚠️ Critical Data Quality Notes

### 1. Null Product Split Offering Group

**What it means**: Opportunity is likely in **Discover stage** where:
- Sales rep converted a lead to opportunity
- Rep hasn't started working on the opportunity yet
- No products have been added to the quote
- No primary product of interest has been selected

**These are VALID bookings** - the rep will add products as they progress the opportunity.

### 2. Forecast Categories

Valid values (after excluding 'Omitted'):
- **Pipeline**: Early stage opportunities
- **Commit**: Committed deals expected to close
- **Best Case**: Likely to close
- **Closed**: Already closed deals

**Always exclude**: `trx_crm_forecast_category <> 'Omitted'`

## 📅 Fiscal Calendar & Date Handling

### Fiscal Year Structure
- **Q1**: January - March
- **Q2**: April - June
- **Q3**: July - September
- **Q4**: October - December

### Dynamic Current Quarter Calculation

```sql
-- Always use this formula for current quarter
TRX_DATE_FISCAL_YEAR_QUARTER = TO_CHAR(CURRENT_DATE, 'YYYY') || '-Q' || TO_CHAR(CEIL(EXTRACT(MONTH FROM CURRENT_DATE) / 3))

-- Examples:
-- January → 2025-Q1
-- June → 2025-Q2
-- October → 2025-Q4
```

### Quarter Format
Always use format: `'YYYY-QN'`
- Examples: '2025-Q1', '2024-Q4', '2025-Q3'

---
