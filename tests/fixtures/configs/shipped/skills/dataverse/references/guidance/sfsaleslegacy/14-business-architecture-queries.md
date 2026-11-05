<!-- sfsaleslegacy · from 04-few-shot-examples-from-subject-matter-ex-2.md -->
### Business Architecture Queries

**Natural Language Query**: "For Sales Group Vodafone, can you show me the history of discounting for the RHEL offering group?"
```sql
WITH filtered_accounts AS (
      SELECT ID
    FROM SFSALESLEGACY_DB.ENTERPRISE_APPLICATION_MARTS.ENTERPRISE_ACCOUNT
      WHERE NAME ILIKE '%Vodafone%'
  ),
filtered_products AS (
      SELECT ID
    FROM SFSALESLEGACY_DB.ENTERPRISE_APPLICATION_MARTS.ENTERPRISE_PRODUCT
      WHERE NAME ILIKE '%RHEL%'
  )
  SELECT
    o.CLOSE_DATE,
    p.NAME AS PRODUCT_NAME,
    p.PRODUCT_CODE,
    a.NAME AS ACCOUNT_NAME,
    oli.LIST_PRICE,
    oli.UNIT_PRICE,
    (oli.LIST_PRICE - oli.UNIT_PRICE) / NULLIF(oli.LIST_PRICE, 0) * 100 AS EFFECTIVE_DISCOUNT_PERCENT
FROM SFSALESLEGACY_DB.ENTERPRISE_APPLICATION_MARTS.ENTERPRISE_OPPORTUNITY_LINE_ITEM AS oli
JOIN SFSALESLEGACY_DB.ENTERPRISE_APPLICATION_MARTS.ENTERPRISE_OPPORTUNITY AS o ON oli.OPPORTUNITY_ID = o.ID
JOIN SFSALESLEGACY_DB.ENTERPRISE_APPLICATION_MARTS.ENTERPRISE_ACCOUNT AS a ON o.ACCOUNT_ID = a.ID
JOIN SFSALESLEGACY_DB.ENTERPRISE_APPLICATION_MARTS.ENTERPRISE_PRODUCT AS p ON oli.PRODUCT_2_ID = p.ID
WHERE a.ID IN (SELECT ID FROM filtered_accounts)
  AND p.ID IN (SELECT ID FROM filtered_products)
  AND o.STAGE_NAME = 'Closed Booked'
  AND oli._fivetran_active = true
  AND a._fivetran_active = true
  AND o._fivetran_active = true
  AND p._fivetran_active = true
  AND oli.UNIT_PRICE >= 0
  AND oli.UNIT_PRICE <= oli.LIST_PRICE
  AND oli.LIST_PRICE > 0
ORDER BY o.CLOSE_DATE DESC;
```
