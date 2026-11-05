<!-- expensemaster · from 10-it-forecast-future-spend-apptio-tables-1.md -->
### Technology Business Management (TBM) Background

#### Cost Types in Apptio Data

**Financial Costs**

- **Definition**: Actual accounting data from financial systems (ERP, General Ledger)
- **Shows**: What was actually spent, invoiced, or forecasted
- **Follows**: Traditional accounting rules and periods
- **Examples**: Invoice amounts, PO commitments, payroll expenses
- **Used for**: Budgeting, vendor payments, financial reporting
- **Tables**: `ITPF_FORECAST_DAILY_CURRENT` and `ITPF_CONTRACT_FORECAST_W_DELEGATION` use financial costs

**Modeled Costs**

- **Definition**: Calculated/allocated costs using TBM methodologies
- **Shows**: True cost of ownership for services/applications
- **Note**: Does not include forecasts
- **Method**: Distributes shared costs using drivers and allocation rules
- **Examples**: Data center costs allocated by server usage, network costs by bandwidth
- **Used for**: Chargeback, decision-making, cost optimization
- **Tables**: `APP_SPEND_BY_*` and `SERVICE_COST_BY_*` tables use modeled costs

#### Key TBM Concepts

- **Cost Pools**: High-level financial categories — External Labor, Facilities & Power, Hardware, Internal Labor, Other, Outside Services, Software, Telecom. APP_SPEND_BY_COST_POOL_MONTHLY and SERVICE_COST_BY_COST_POOL_MONTHLY break down by these.
- **Resource Towers**: Functional IT groupings — Application, Compute, Data Center, Delivery, End User, IT Management, Network, Platform, Security & Compliance, Storage. APP_SPEND_BY_TOWER_MONTHLY and SERVICE_COST_BY_TOWER_MONTHLY break down by these.
- **TBM Taxonomy**: Common language for classifying technology costs
