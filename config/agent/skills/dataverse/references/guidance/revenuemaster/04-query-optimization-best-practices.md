<!-- revenuemaster · from 01-critical-table-volumes-query-performance.md -->
### ✅ Query Optimization Best Practices

1. **Filter Early**: Always apply date filters at the CTE level before joins
2. **Use Date Ranges**: Use `gl_date >= 'YYYY-01-01' AND gl_date < 'YYYY+1-01-01'` instead of `YEAR(gl_date) = YYYY`
3. **Aggregate Early**: Use `GROUP BY` and `HAVING` in CTEs to reduce row counts before window functions
4. **Anti-Join Pattern**: Replace `NOT IN (subquery)` with `LEFT JOIN ... WHERE IS NULL`
5. **Avoid Multi-Way Joins**: Use UNION ALL pattern when combining data from multiple tables
6. **Limit Result Sets**: Add `HAVING SUM(amount) > threshold` to filter out immaterial amounts early
