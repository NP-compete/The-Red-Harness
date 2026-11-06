<!-- expensemaster · from 11-it-forecast-future-spend-apptio-tables-2.md -->
### What Apptio Data CANNOT Answer

- **IT booked actuals as system of record**: Total or period **actual** IT spend that mirrors the **general ledger** (e.g. *"What was IT spend in 2025?"*) → **`GL_SUB_LEDGER_AGGREGATE`** / **OneStream Actual** — not Apptio by default.
- **Non-IT Spend**: Apptio only contains IT department data (e.g. vending machines, non-IT facilities → use GL/OneStream).
- **Lease Data**: RH tower and other lease information not included.
- **Real-time Data**: Forecasts are based on snapshot data, not live.
- **Attribution/Reasoning**: "Why did costs increase?" — can show what increased, not why.

### Apptio Constraints & Guardrails

1. **IT Only**: All Apptio tables contain only IT spend and forecast data.
2. **Forecast Cycles**: Data is snapshotted by forecast entry month — always filter for latest.
3. **C&B Limitation**: Labor costs not forecasted beyond current year.
4. **TCO vs Financial**: APP_SPEND and SERVICE_COST tables show modeled TCO (OpEx only), not financial actuals.

### Apptio domain experts

- **Apptio Portal**: https://redhatit.apptio.com/
- **Contact**: TBMO@redhat.com, jfarnham@redhat.com, andschne@redhat.com

For column definitions and table schemas, refer to the YAML files in `expensemaster-dbt/models/rhai_marts/`.

---
