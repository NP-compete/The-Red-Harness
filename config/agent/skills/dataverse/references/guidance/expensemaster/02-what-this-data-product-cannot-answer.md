<!-- expensemaster · from 01-question-coverage-which-tables-to-use.md -->
## ❌ What This Data Product CANNOT Answer

- **Revenue / cash / profit**: ACV, TCV, subscription counts, cash flow timing, net profit, operating margin.
- **CapEx in GL/OneStream**: Those tables are OpEx only; for IT CapEx use [Apptio (ITPF) tables](#it-forecast--future-spend-apptio-tables).
- **Attribution**: "Why did spend increase?" — you can show what increased, not why.
- **Targets**: Revenue or non-expense goals.
- **Total company spend with a hyperscaler from the Cloudability mart alone** — that mart is the **Cloudability cloud slice**; **full booked vendor totals** live on **GL** (`GL_SUB_LEDGER_AGGREGATE`).

When a request is out of scope, say so and offer what *is* in scope (e.g. variance, load rate, spend by department/vendor/account, rankings, headcount, IT forecast from Apptio, or Cloudability-tracked cloud spend).
