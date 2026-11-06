<!-- sfsaleslegacy · from 01-sfsaleslegacy-data-product-knowledge-bas.md -->
#### PSA_MARTS (12 Views) - **PROFESSIONAL SERVICES AUTOMATION**
* **Purpose**: Specialized schema for Professional Services Automation with **unique PSA-specific tables** not available in other marts. Critical for services delivery, project management, and consultant operations.
* **Business Use Cases**: **~50% of legacy users** (750+ of 1500 total users) are PSA-focused, including project managers, services teams, and financial planning for services
* **Real Business Requirements**:
  * **Timecards**: All timecard data with history, approvals, amendments for backtracking
  * **Resource Management**: Internal/contractor hours (current/prior year), cost rates, utilization
  * **Project Management**: Projects, milestones, tasks, OPA numbers, billable/non-billable tracking
  * **Financial Planning**: Services yield analysis, budget vs actual, project profitability
* **When to Use**: Select this mart **only** for professional services questions:
  * **Timecard Analysis**: "billable hours", "timecard", "consultant utilization", "project hours"
  * **Project Management**: "project status", "milestones", "project budget", "assignments"
  * **Services Financial**: "project margin", "consulting units", "yield analysis", "cost rates"
  * **Client Satisfaction**: CSAT scores and feedback related to service delivery
  * **Supporting Tables Unique to PSA**: psa_pse_proj, psa_pse_timecard, psa_pse_assignment, psa_pse_budget, psa_pse_milestone, psa_pse_est_vs_actuals
  * **Critical Considerations**:
  * **Historical Preservation**: Some views (psa_pse_timecard, psa_pse_milestone) intentionally preserve all historical data
  * **Complex Integration**: Often requires joining multiple PSA tables for complete analysis
  * **High Detail**: Extremely wide tables (295+ fields) - be precise in column selection
