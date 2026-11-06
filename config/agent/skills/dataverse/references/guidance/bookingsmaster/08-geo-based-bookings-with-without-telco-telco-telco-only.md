<!-- bookingsmaster · from 02-critical-business-rules-always-apply-1.md -->
### 4. Geo based Bookings with/without Telco (TELCO_TELCO) only:

**CRITICAL for Telco reporting**: When user asks for Country/Subregion/Region bookings but with ot without TELCO_TELCO along with each geo then use this scenarion.

**Why**: Telco is a geo sepration even though its not a location; reporting requires visibility by country or subregion or Region. Returning "all Telco" as one number pulls in every telco split and is not the intended use.

```sql
-- ✅ CORRECT - Pick the country to region/subregion mapping first and then show the bookings by Geo and for the given fiscal quarter. This sample to query bookings for Subregion = MENA and for fiscal year = 2025

with country_region_map as(
select distinct trx_account_billing_country,trx_account_subregion,trx_account_region,trx_account_geo from bookingsmaster_db.marts.transaction_account where trx_account_subregion='MENA'
)

select distinct
trx_date_fiscal_year_number,trx_split_geo,sum(tcv_amount_usd_cy_pr),sum(acv_plus_amount_usd_cy_pr) from bookingsmaster_db.marts.eoq_transaction_acv_snapshot acv   join country_region_map on (acv.trx_country_of_order=country_region_map.trx_account_billing_country)
where  acv.trx_date_fiscal_year_number in ('2025') and bookings_flag='Y' --and trx_split_geo in ('EMEA_EMEA','TELCO_TELCO')
group by all
;

-- ❌ WRONG - Single aggregated Telco total (do not do this)
-- WHERE trx_split_geo = 'TELCO_TELCO'
-- GROUP BY ...  (no breakdown by country/subregion)
```

**Rule**: For any query that filters on or reports by `trx_split_geo = 'TELCO_TELCO'`, include a dimension such as `trx_split_region`, reporting_country, or subregion in the SELECT and GROUP BY so results are split by geography.

---
