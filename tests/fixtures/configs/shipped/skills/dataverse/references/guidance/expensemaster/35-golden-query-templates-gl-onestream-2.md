<!-- expensemaster · from 09-golden-query-templates-gl-onestream-2.md -->
EXPENSE_CATEGORY> || '%'  -- e.g., '%Software%'
  AND YEAR(period_date) = YEAR(CURRENT_DATE())
GROUP BY vendor_customer
ORDER BY total_usd DESC
LIMIT 10;
```

**Common Expense Categories**:
- Software, Software Maintenance and Support Services, Software Maintenance and Support Prepaid
