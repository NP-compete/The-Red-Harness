<!-- bookingsmaster · from 02-critical-business-rules-always-apply-1.md -->
### 7. Key Metric Definitions

**Core Metrics**:
1. **ARR** (Annual Recurring Revenue) - Subscription revenue
2. **ACV** (Annual Contract Value) - Contract value excluding consumption
3. **TCV** (Total Contract Value) - Total booking including multi-year
4. **ACV+** (ACV Plus) - ACV including consumption premium drawdowns
5. **ACV+ Drawdown** - Just the HCS hybrid committed spend drawdowns
6. **SEAP ACV** (Subscription Education Awareness Program) - SEAP-specific annual contract value

**⚠️ SEAP (Subscription Education Awareness Program)**:
- SEAP is **NOT a region** — it is a program. Snowflake column comments may say "SEAP region processing" but this is misleading.
- For SEAP ACV, **do NOT** filter by `TRX_SEAP_FLAG = 'Y'` and sum `ACV_PLUS_AMOUNT_USD_CY_PR` — this returns the full ACV+ of every SEAP-flagged transaction and produces massively inflated values (~10x overstatement).
- SEAP is all ACV, so the correct column is `TCV_AMOUNT_SEAP_USD_CY_PR` which contains only the SEAP-specific portion.
- All standard bookings filters still apply (exclude IBM, remove Omitted, etc.).

```sql
-- ✅ CORRECT: SEAP ACV using TCV_AMOUNT_SEAP_USD_CY_PR
SELECT
    TRX_DATE_FISCAL_YEAR_NUMBER,
    SUM(TCV_AMOUNT_SEAP_USD_CY_PR) AS seap_acv_usd
FROM BOOKINGSMASTER_DB.MARTS.PIPELINE_TRANSACTIONS_ACV
WHERE BOOKINGS_FLAG = 'Y'
  AND TRX_CRM_FORECAST_CATEGORY <> 'Omitted'
  AND TCV_AMOUNT_SEAP_USD_CY_PR <> 0
  AND TRX_DATE_FISCAL_YEAR_NUMBER = 2025
GROUP BY TRX_DATE_FISCAL_YEAR_NUMBER

-- ❌ WRONG: Do NOT use this approach for SEAP ACV
-- WHERE TRX_SEAP_FLAG = 'Y'
-- SUM(ACV_PLUS_AMOUNT_USD_CY_PR)  -- Returns ~$1.5B instead of correct ~$146M
```

---
