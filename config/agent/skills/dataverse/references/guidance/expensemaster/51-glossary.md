<!-- expensemaster · from 12-cloudability-cloud-spend-cloudability_co.md -->
## 📚 Glossary

| Term | Definition | Table Reference |
|------|------------|-----------------|
| **Actuals** | Real-world expenses finalized and recorded | `GL_SUB_LEDGER_AGGREGATE`, `ONESTREAM_FINANCIAL_AGGREGATE` |
| **Accruals** | Expenses recognized before paid (matching expense to period) | `GL_SUB_LEDGER_AGGREGATE` |
| **Amortization** | Gradual write-off of asset cost over its useful life | `GL_SUB_LEDGER_AGGREGATE` |
| **Budget (Plan)** | Financial plan set at beginning of fiscal year | `ONESTREAM_FINANCIAL_AGGREGATE` |
| **Cost Center Code** | Organizational unit (department/team) responsible for costs | All tables |
| **Forecast** | Updated estimate of future spend, adjusted as actuals come in | `ONESTREAM_FINANCIAL_AGGREGATE` |
| **Headcount** | Employee count by period and cost center | `ONESTREAM_HEADCOUNT_AGGREGATE` |
| **Geo / Region** | Geographic classification (NA, EMEA, APAC, LATAM) | All tables |
| **MTD / QTD / YTD** | Month-to-Date, Quarter-to-Date, Year-to-Date | All tables |
| **OpEx** | Operating Expenses—day-to-day costs. GL and OneStream are OpEx only. | `GL_SUB_LEDGER_AGGREGATE`, `ONESTREAM_FINANCIAL_AGGREGATE` |
| **CapEx** | Capital expenditures. Only in Apptio (ITPF) tables; use `EXPENSE_TYPE`. | ITPF_* tables |
| **Variance** | Difference between Actual vs. Forecast (positive = overspend) | `ONESTREAM_FINANCIAL_AGGREGATE` |
| **Vendor / PO** | Supplier and purchase order details | `GL_SUB_LEDGER_AGGREGATE` |
| **Cloudability mart** | Hyperscaler cloud charges with OneStream enrichment — see **`expensemaster-dbt/docs/cloudability_cost_info.md`** | `CLOUDABILITY_COST_INFO` |
