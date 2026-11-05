<!-- bookingsmaster · from 02-critical-business-rules-always-apply-1.md -->
### 1. Default to Current Year/Quarter When Not Specified

**CRITICAL**: When user doesn't specify a year or quarter, **ALWAYS default to CURRENT year/quarter**.

**Examples of Ambiguous Queries**:
- "What is Q3 ARR?" → Default to **current year** Q3
- "Show me total ACV+" → Default to **current quarter**
- "Pipeline for RHEL" → Default to **current quarter**

**Implementation**:
```sql
-- ✅ CORRECT - Always default to current year when not specified
WHERE revenue_recognition_date_fiscal_year_quarter =
    TO_CHAR(CURRENT_DATE, 'YYYY') || '-Q3'  -- Current year Q3

-- ✅ CORRECT - Always default to current quarter when period not specified
WHERE TRX_DATE_FISCAL_YEAR_QUARTER =
    TO_CHAR(CURRENT_DATE, 'YYYY') || '-Q' || TO_CHAR(CEIL(EXTRACT(MONTH FROM CURRENT_DATE) / 3))

-- ❌ WRONG - Don't assume past year
WHERE revenue_recognition_date_fiscal_year_quarter = '2024-Q3'  -- Only use if user explicitly said 2024
```

**Rule**: Unless user explicitly states a different year, use `TO_CHAR(CURRENT_DATE, 'YYYY')` for the year component.
