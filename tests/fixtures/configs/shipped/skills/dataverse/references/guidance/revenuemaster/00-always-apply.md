<!-- revenuemaster · the rules that apply to every query here -->
# Always apply — revenuemaster

Read this before writing any SQL for this product. Everything
below applies regardless of what the question asks.

## ⚠️ CRITICAL: Table Volumes & Query Performance

### 6. IBM Contingencies Exclusion
- **Standard revenue analysis excludes** revenue related to IBM contingencies including:
  - Intercompany transactions with IBM
  - Cloud Pak revenue splits
  - Revenue splits with IBM
- These components are tracked separately in Division RT revenue views
- **Note**: Unless specifically asked about IBM-related revenue, exclude these components from analysis
- **External revenue** refer to the revenue_external view and always use filter is_intercompany = 0

### 7. Year-over-Year (YoY) Comparisons - Apples-to-Apples Rule
- **CRITICAL**: For incomplete periods, ALWAYS compare matching date ranges from prior year
- **Example**: If today is Dec 17, 2025:
  - Current Period: Dec 1-17, 2025 (or Oct 1-Dec 17 for QTD)
  - Prior Period: Dec 1-17, 2024 (or Oct 1-Dec 17 for QTD)
  - **NEVER** compare incomplete Q4 2025 (through Dec 17) with complete Q4 2024 (through Dec 31)
- **Implementation**: Use `DATEADD(year, -1, CURRENT_DATE)` to match exact prior year date
- **Always append**: "as of [current date]" when describing YoY comparisons for incomplete periods
- **Indicator**: Clearly state "incomplete period - apples-to-apples through [date]" in results

### 🚨 Performance Anti-Patterns to AVOID

**1. NEVER use functions on date columns in WHERE clauses:**
```sql
-- ❌ BAD: Prevents micro-partition pruning, scans ALL 415M rows
WHERE YEAR(gl_date) = 2025

-- ✅ GOOD: Enables partition pruning, scans only relevant partitions
WHERE gl_date >= '2025-01-01' AND gl_date < '2026-01-01'
```

**2. NEVER use `NOT IN` with subqueries on large tables:**
```sql
-- ❌ BAD: Materializes millions of rows, then compares each row
WHERE arrangement_number NOT IN (
    SELECT DISTINCT arrangement_number
    FROM revenuemaster_db.marts.go_to_market_revenue
    WHERE YEAR(gl_date) = 2025
)

-- ✅ GOOD: Use LEFT JOIN with IS NULL (anti-join pattern)
LEFT JOIN (
    SELECT DISTINCT arrangement_number
    FROM revenuemaster_db.marts.go_to_market_revenue
    WHERE gl_date >= '2025-01-01' AND gl_date < '2026-01-01'
) gtm ON fpa.arrangement_number = gtm.arrangement_number
WHERE gtm.arrangement_number IS NULL
```

**3. NEVER join large tables without pre-filtering:**
```sql
-- ❌ BAD: Joins 415M × 17M × 14M rows before filtering
FROM go_to_market_revenue gtm
LEFT JOIN revenue_by_offering rbo ON gtm.arrangement_number = rbo.revenue_arrangement_number
LEFT JOIN revenue_foundation_fpa_adjustments fpa ON gtm.arrangement_number = fpa.arrangement_number
WHERE YEAR(gtm.gl_date) = 2025

-- ✅ GOOD: Pre-filter each table in CTEs, then join smaller datasets
WITH gtm_2025 AS (
    SELECT * FROM go_to_market_revenue
    WHERE gl_date >= '2025-01-01' AND gl_date < '2026-01-01'
),
rbo_2025 AS (
    SELECT * FROM revenue_by_offering
    WHERE revenue_gl_date >= '2025-01-01' AND revenue_gl_date < '2026-01-01'
)
SELECT ... FROM gtm_2025 gtm LEFT JOIN rbo_2025 rbo ON ...
```

**4. NEVER create Cartesian explosions with multiple LEFT JOINs:**
```sql
-- ❌ BAD: If arrangement has 10 RBO rows and 5 FPA rows, creates 50 output rows
FROM gtm
LEFT JOIN rbo ON gtm.arrangement_number = rbo.arrangement_number
LEFT JOIN fpa ON gtm.arrangement_number = fpa.arrangement_number

-- ✅ GOOD: Use UNION ALL to combine data sources separately
SELECT ... FROM gtm LEFT JOIN rbo ON ...
UNION ALL
SELECT ... FROM fpa WHERE fpa.arrangement_number NOT IN (SELECT arrangement_number FROM gtm)
```
