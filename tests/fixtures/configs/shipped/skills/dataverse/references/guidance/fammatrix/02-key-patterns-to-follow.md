<!-- fammatrix · from 01-quick-start.md -->
### 🎯 KEY PATTERNS TO FOLLOW

1. **Organization Analysis** → Simple GROUP BY with COUNT
2. **Department Searches** → Use LIKE for flexibility: `DEPT_1 LIKE '%Marketing%' OR DEPT_1 = 'MKT'`
3. **Financial Manager Lists** → Always exclude `#N/A%` values
4. **CLT Assignments** → Check ALL CLT columns: `CLT IS NOT NULL OR CLT_1 IS NOT NULL OR CLT_2 IS NOT NULL`
5. **Large Result Sets** → Add LIMIT clause (typically 20-50 rows)
6. **EMEA/Regional Questions** → Usually means ALL records, not filtering by region

---

## 📊 DEPARTMENT CODES

### DEPT_1 (Top Level — 4 values)
- `CORP` = "Corporate" / "Corporate Functions" (211 centers)
- `Total_SnS` = "Sales" / "Services" / "Sales & Services" (205 centers)
- `PnGE` = "Product" / "Engineering" / "Product & Engineering" (144 centers)
- `MKT` = "Marketing" (59 centers)

### DEPT_2 (9 values)
- Under CORP: `GnA_Consol_IBM_RH` (210), `CPJ` (1)
- Under Total_SnS: `SLS` (Sales-159), `RSS` (Services-46)
- Under PnGE: `Global_Engineering` (108), `Products` (36)
- Under MKT: `Corporate_Marketing` (25), `Global_Demand_Marketing` (17), `Product_Marketing_Program_Spend` (15)
