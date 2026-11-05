<!-- expensemaster · from 04-column-selection-guide-department-vs-acc-1.md -->
### Amount columns (when to use which)

| Column | Meaning | Use when |
|--------|---------|----------|
| `amount_usd` | Amount at **plan rate at time of transaction** (transaction-level plan rate) | **Default** for all queries: single-period, multi-period, and YoY comparisons |
| `amount_usd_current_plan_year` | Amount restated at **current year's plan rate** | **Only** when the user explicitly asks for current plan rate in their query |

**When to use `amount_usd_current_plan_year`:**
**Before choosing the amount column**, scan the user's query for: **"using the current plan rate"**, **"use the current plan rate"**, **"current plan rate"**, **"at current plan rate"**, or **"current year plan rate"**. If any of these phrases appear, use **`amount_usd_current_plan_year`** in every SUM (including all CASE expressions in YoY queries). Otherwise use **`amount_usd`**. Do not assume every YoY question uses current plan rate—only when the user explicitly includes one of these phrases.

**Examples:**
- "What is IT spend this year vs last year?" → Use **`amount_usd`** (default).
- "Who were the top 5 vendors in IT in CY25? How do they compare to the year prior? **Use the current plan rate**." → Use **`amount_usd_current_plan_year`** (user said "use the current plan rate").
- "**Using the current plan rate**, who were the top 5 vendors driving spend in the IT organization in CY25? How do they compare to the year prior?" → Use **`amount_usd_current_plan_year`**.
- "Compare Benefits Load Rate Q4 2025 to Q4 2024 **using the current plan rate**." → Use **`amount_usd_current_plan_year`**.
