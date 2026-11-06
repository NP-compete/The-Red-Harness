<!-- expensemaster · from 12-cloudability-cloud-spend-cloudability_co.md -->
### Sample questions

**How did our Amazon spend change between January and February 2026 for cost center 592?**

```sql
SELECT
    MAX('Filtered by: period_date 2026-01-01 - 2026-02-28, vendor Amazon, cost_center_code 592; SUM(period_amount) from EXPENSEMASTER_DB.RHAI_MARTS.CLOUDABILITY_COST_INFO (not GL plan-rate).') AS _filter_note,
    MONTH(period_date) AS cost_month,
    SUM(period_amount) AS total_cloud_spend
FROM EXPENSEMASTER_DB.RHAI_MARTS.CLOUDABILITY_COST_INFO
WHERE period_date >= '2026-01-01'
  AND period_date <= '2026-02-28'
  AND vendor = 'Amazon'
  AND cost_center_code = '592'
GROUP BY MONTH(period_date)
ORDER BY cost_month;
```

**How did our total spend across AWS and GCP change between Q3 and Q4 of 2025?**

```sql
SELECT
    MAX('Filtered by: period_date 2025-07-01 - 2025-12-31, vendors Amazon and GCP; SUM(period_amount) from EXPENSEMASTER_DB.RHAI_MARTS.CLOUDABILITY_COST_INFO (not GL plan-rate).') AS _filter_note,
    QUARTER(period_date) AS cost_quarter,
    vendor,
    SUM(period_amount) AS total_cloud_spend
FROM EXPENSEMASTER_DB.RHAI_MARTS.CLOUDABILITY_COST_INFO
WHERE period_date >= '2025-07-01'
  AND period_date <= '2025-12-31'
  AND vendor IN ('Amazon', 'GCP')
GROUP BY QUARTER(period_date), vendor
ORDER BY cost_quarter, vendor;
```

**Show me the top 5 most expensive cloud accounts in December 2025.**

```sql
SELECT
    MAX('Filtered by: period_date 2025-12-01 - 2025-12-31; top 5 by SUM(period_amount); EXPENSEMASTER_DB.RHAI_MARTS.CLOUDABILITY_COST_INFO (not GL plan-rate).') AS _filter_note,
    account_name,
    SUM(period_amount) AS total_cloud_spend
FROM EXPENSEMASTER_DB.RHAI_MARTS.CLOUDABILITY_COST_INFO
WHERE period_date >= '2025-12-01'
  AND period_date <= '2025-12-31'
GROUP BY account_name
ORDER BY total_cloud_spend DESC
LIMIT 5;
```

**Which cost center and account spent the most on Azure in Q1 2026?** *(Adjust `QUARTER` / `YEAR` for other calendar quarters.)*

```sql
SELECT
    MAX('Filtered by: Q1 2026, vendor Azure; top 5 by SUM(period_amount); EXPENSEMASTER_DB.RHAI_MARTS.CLOUDABILITY_COST_INFO (not GL plan-rate).') AS _filter_note,
    QUARTER(period_date) AS cost_quarter,
    cost_center_code,
    account_name,
    SUM(period_amount) AS total_cloud_spend
FROM EXPENSEMASTER_DB.RHAI_MARTS.CLOUDABILITY_COST_INFO
WHERE QUARTER(period_date) = 1
  AND YEAR(period_date) = 2026
  AND vendor = 'Azure'
GROUP BY QUARTER(period_date), cost_center_code, account_name
ORDER BY total_cloud_spend DESC
LIMIT 5;
```

**What was IT organization cloud spend in Q2 2025?** *(Pattern B — IT is not a known department; use [Hierarchy Matching Rule](#-critical-hierarchy-matching-rule-avoid-false-positives).)*

```sql
SELECT
    MAX('Filtered by: period_date 2025-04-01 - 2025-06-30, org IT (Pattern B: department or hierarchy REGEXP); SUM(period_amount) from EXPENSEMASTER_DB.RHAI_MARTS.CLOUDABILITY_COST_INFO (not GL plan-rate).') AS _filter_note,
    QUARTER(period_date) AS cost_quarter,
    SUM(period_amount) AS total_cloud_spend
FROM EXPENSEMASTER_DB.RHAI_MARTS.CLOUDABILITY_COST_INFO
WHERE period_date >= '2025-04-01'
  AND period_date <= '2025-06-30'
  AND (
        cost_center_department = 'IT'
        OR REGEXP_LIKE(cost_center_hierarchy, '(^|.*[|])' || 'IT' || '[_|].*')
      )
GROUP BY QUARTER(period_date)
ORDER BY cost_quarter;
```

**What was cloud spend for the Sales department in July 2025?** *(Pattern A — Sales is a known department; exact match on `cost_center_department` only.)*

```sql
SELECT
    MAX('Filtered by: period_date 2025-07-01 - 2025-07-31, cost_center_department Sales; SUM(period_amount) from EXPENSEMASTER_DB.RHAI_MARTS.CLOUDABILITY_COST_INFO (not GL plan-rate).') AS _filter_note,
    MONTH(period_date) AS cost_month,
    SUM(period_amount) AS total_cloud_spend
FROM EXPENSEMASTER_DB.RHAI_MARTS.CLOUDABILITY_COST_INFO
WHERE period_date >= '2025-07-01'
  AND period_date <= '2025-07-31'
  AND cost_center_department = 'Sales'
GROUP BY MONTH(period_date)
ORDER BY cost_month;
```

---
