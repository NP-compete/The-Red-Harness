<!-- expensemaster · from 01-question-coverage-which-tables-to-use.md -->
## 🔗 Shared conventions

- **Database & schema:** GL, OneStream, headcount, **Apptio** (ITPF_*, APP_SPEND_*, SERVICE_COST_*), and **Cloudability** (CLOUDABILITY_COST_INFO) queries use **`EXPENSEMASTER_DB.RHAI_MARTS`**. Do not mix schemas in one query unless you explicitly join across them.
- **Schema precedence for GL & OneStream (RLS rollout):** If the user has access to both **`EXPENSEMASTER_DB.RHAI_MARTS`** and **`EXPENSEMASTER_DB.TEST_MARTS`**, prefer the GL/OneStream tables in **`EXPENSEMASTER_DB.TEST_MARTS`**. Use **`EXPENSEMASTER_DB.RHAI_MARTS`** only when TEST_MARTS access (or required table) is unavailable.
- **RLS scope note:** Row-level security (RLS) may apply to GL/OneStream outputs (for example, when routed to TEST_MARTS during rollout). Treat returned data as access-scoped to the user's authorized cost centers.
- **Per–data source:** Apply the critical rules (below) for your chosen source; use this README's source section for column/filter guidance and query patterns. When you have access to dbt mart YAML, use it for table selection (USE THIS TABLE WHEN) and column definitions. Always apply the rules for the source you chose from [Question coverage](#question-coverage-which-tables-to-use).
