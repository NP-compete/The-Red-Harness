<!-- bookingsmaster · from 10-common-mistakes-to-avoid.md -->
### 7. ❌ Not Defaulting to Current Year When Not Specified

**Wrong** (assuming past year when user says "Q3 ARR"):
```sql
-- User asks: "What is Q3 ARR?"
WHERE revenue_recognition_date_fiscal_year_quarter = '2024-Q3'  -- Assumes 2024!
```

**Right**:
```sql
-- User asks: "What is Q3 ARR?" → Default to CURRENT year
WHERE revenue_recognition_date_fiscal_year_quarter = TO_CHAR(CURRENT_DATE, 'YYYY') || '-Q3'
```

**Rule**: Unless user explicitly states a different year, ALWAYS default to current year using `TO_CHAR(CURRENT_DATE, 'YYYY')`.

---
