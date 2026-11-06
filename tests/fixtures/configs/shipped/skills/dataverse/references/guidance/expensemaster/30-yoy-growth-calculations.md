<!-- expensemaster · from 07-business-definitions-logic-gl-onestream.md -->
### YoY Growth Calculations

**CRITICAL - Apples-to-Apples Rule**: For incomplete periods, ALWAYS compare matching date ranges from prior year. Use **`amount_usd`** (default) for YoY comparisons unless the user explicitly asks for "current plan rate" or "current year plan rate"—then use **`amount_usd_current_plan_year`**.

**Example**: If today is Jan 14, 2026:
- Current Period: Jan 1-14, 2026 (or for QTD: current quarter start through Jan 14)
- Prior Period: Jan 1-14, 2025 (or for QTD: same quarter start through Jan 14)
- **NEVER** compare incomplete Jan 2026 (through Jan 14) with complete Jan 2025 (through Jan 31)

**Implementation**: Use `DATEADD('year', -1, CURRENT_DATE())` to match exact prior year date

**Response Requirements**:
- Always append "as of [current date]" when describing YoY comparisons for incomplete periods
- Clearly state "incomplete period - apples-to-apples through [date]" in results

```sql
-- CORRECT: Compare exact same time periods. Uses amount_usd (default); use amount_usd_current_plan_year only if user asked for "current plan rate".
-- Always caveat if comparing partial periods
WITH current_year AS (
    SELECT SUM(amount_usd) as cy_spend
    FROM EXPENSEMASTER_DB.RHAI_MARTS.GL_SUB_LEDGER_AGGREGATE
    WHERE period_date BETWEEN DATE_TRUNC('year', CURRENT_DATE()) AND CURRENT_DATE()
),
prior_year AS (
    SELECT SUM(amount_usd) as py_spend
    FROM EXPENSEMASTER_DB.RHAI_MARTS.GL_SUB_LEDGER_AGGREGATE
    WHERE period_date BETWEEN DATEADD('year', -1, DATE_TRUNC('year', CURRENT_DATE()))
                          AND DATEADD('year', -1, CURRENT_DATE())
)
SELECT
    cy.cy_spend,
    py.py_spend,
    (cy.cy_spend - py.py_spend) / NULLIF(py.py_spend, 0) * 100 as yoy_growth_pct,
    'Data as of ' || CURRENT_DATE() || ' (partial period comparison)' as caveat
FROM current_year cy, prior_year py;
```
