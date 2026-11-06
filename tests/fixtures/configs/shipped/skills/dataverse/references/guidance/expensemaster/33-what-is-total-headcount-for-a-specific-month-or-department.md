<!-- expensemaster · from 08-golden-query-templates-gl-onestream-1.md -->
### 7.3 What is total headcount for a specific month or department?

**⚠️ CRITICAL - Headcount Period Rules**:

Headcount data is a **monthly snapshot** taken on the first of each month.

| Period Type | Rule | Example |
|-------------|------|---------|
| Single month (e.g., "January 2025") | Use that month's snapshot | `period_date = '2025-01-01'` |
| Multi-month period (e.g., "Q1 2025", "H1 2025", "YTD") | Use ONLY the **last month** in the period | Q1 → `period_date = '2025-03-01'` (March only) |

**🚫 NEVER sum headcount across multiple months** - this causes double/triple counting since the same employees appear in each monthly snapshot.

**Multi-Month Period Reference** (use the last month only):
- Q1: Use March (`'2025-03-01'`)
- Q2: Use June (`'2025-06-01'`)
- Q3: Use September (`'2025-09-01'`)
- Q4: Use December (`'2025-12-01'`)
- H1 (First Half): Use June (`'2025-06-01'`)
- H2 (Second Half): Use December (`'2025-12-01'`)
- Full Year / YTD: Use December (`'2025-12-01'`) or current month if incomplete year

**Example 1: Total headcount for a specific month (all departments)**

```sql
-- What was the total headcount as of January 2025?
SELECT
   SUM(headcount_amount) as total_headcount
FROM EXPENSEMASTER_DB.RHAI_MARTS.ONESTREAM_HEADCOUNT_AGGREGATE
WHERE period_date = '2025-01-01'
  AND scenario = 'Actual';
```

**Example 2: Headcount for a specific department**

> **Note**: Apply the Common Aliases translations before searching (e.g., "Marketing" should search both `cost_center_department` and `cost_center_hierarchy`).

```sql
-- What was the headcount for Marketing as of January 2025?
SELECT
   SUM(headcount_amount) as total_headcount
FROM EXPENSEMASTER_DB.RHAI_MARTS.ONESTREAM_HEADCOUNT_AGGREGATE
WHERE period_date = '2025-01-01'
  AND scenario = 'Actual'
  AND (cost_center_department = 'Marketing Department'
       OR REGEXP_LIKE(cost_center_hierarchy, '(^|.*[|])Marketing[_|].*'));
```

**Example 3: Headcount breakdown by department**

```sql
-- Headcount by department as of January 2025
SELECT
   cost_center_department,
   SUM(headcount_amount) as total_headcount
FROM EXPENSEMASTER_DB.RHAI_MARTS.ONESTREAM_HEADCOUNT_AGGREGATE
WHERE period_date = '2025-01-01'
  AND scenario = 'Actual'
GROUP BY cost_center_department
ORDER BY total_headcount DESC;
```

**Month Date Format**: Use first of month (e.g., '2025-01-01' for January, '2025-12-01' for December)
