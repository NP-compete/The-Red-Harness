<!-- expensemaster · from 02-critical-rules.md -->
### Common (all sources)

- **Schema:** GL/OneStream, Apptio/ITPF/TBM and Cloudability use **`EXPENSEMASTER_DB.RHAI_MARTS`** ([Shared conventions](#-shared-conventions)) unless the GL/OneStream schema precedence rule applies (prefer **`EXPENSEMASTER_DB.TEST_MARTS`** when both are available).
- **Period/date:** Use **`period_date`** (DATE) for filtering on GL, OneStream, Apptio, and Cloudability; do **not** use text fields (`period`, `period_name`) for date logic on GL/Apptio marts.
