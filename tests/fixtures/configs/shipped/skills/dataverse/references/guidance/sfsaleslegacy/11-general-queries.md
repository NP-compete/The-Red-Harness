<!-- sfsaleslegacy · from 03-few-shot-examples-from-subject-matter-ex-1.md -->
### General Queries

**Natural Language Query**: "Show me all Bill To accounts for Vodafone, with their associated addresses"
```sql
  SELECT
      ac.name AS "Sales Account Name",
    ad.address_line_1_c,
    ad.address_line_2_c,
    ad.address_line_3_c,
    ad.address_line_4_c,
    ad.city_c,
    ad.state_c,
    ad.zip_postal_code_c,
    ad.country_c
FROM SFSALESLEGACY_DB.ENTERPRISE_APPLICATION_MARTS.ENTERPRISE_ADDRESS ad
JOIN SFSALESLEGACY_DB.ENTERPRISE_APPLICATION_MARTS.ENTERPRISE_ACCOUNT ac
ON ad.sales_account_c = ac.id
  WHERE ac.name ILIKE '%Vodafone%'
  AND ad.bill_to_address_c = TRUE
  AND ad.status_c = 'Active'
  AND ac._fivetran_active = true
  AND ad._fivetran_active = true;
```

**Natural Language Query**: "What is the mix of products that Vodafone purchased from Red Hat to date?"
```sql
-- Comprehensive product mix analysis with multiple perspectives
  SELECT
    p.product_line_c AS "Product Line",
    p.name AS "Product Name",
    COUNT(DISTINCT o.id) AS "Unique Deals",
    COUNT(*) AS "Total Line Items",
    SUM(oli.quantity) AS "Total Quantity"
FROM SFSALESLEGACY_DB.SFSALES_MARTS.SFSALES_OPPORTUNITY o
JOIN SFSALESLEGACY_DB.SFSALES_MARTS.SFSALES_OPPORTUNITY_LINE_ITEM oli ON oli.opportunity_id = o.id
JOIN SFSALESLEGACY_DB.SFSALES_MARTS.SFSALES_PRODUCT p ON oli.product_2_id = p.id
JOIN SFSALESLEGACY_DB.GENERAL_MARTS.GENERAL_ACCOUNT a ON o.account_id = a.id
WHERE o.is_deleted = 0
  AND o._fivetran_active = 1
  AND oli.is_deleted = 0
  AND oli._fivetran_active = 1
  AND p.is_deleted = 0
  AND p._fivetran_active = 1
  AND a.is_deleted = 0
  AND a._fivetran_active = 1
  AND o.stage_name = 'Closed Booked'
    AND a.name ILIKE '%Vodafone%'
GROUP BY p.product_line_c, p.name
ORDER BY COUNT(DISTINCT o.id) DESC;
```

**Natural Language Query**: "How many distinct won opportunities, with total Line Items has Vodafone had to date?"
```sql
-- distinct won opportunities
SELECT
    COUNT(DISTINCT o.id) AS "Grand Total Distinct Won Opportunities",
    COUNT(*) AS "Total Line Items",
    SUM(COALESCE(oli.quantity, 0)) AS "Total Quantity"
FROM SFSALESLEGACY_DB.SFSALES_MARTS.SFSALES_OPPORTUNITY o
JOIN SFSALESLEGACY_DB.SFSALES_MARTS.SFSALES_OPPORTUNITY_LINE_ITEM oli ON oli.opportunity_id = o.id
JOIN SFSALESLEGACY_DB.SFSALES_MARTS.SFSALES_PRODUCT p ON oli.product_2_id = p.id
JOIN SFSALESLEGACY_DB.GENERAL_MARTS.GENERAL_ACCOUNT a ON o.account_id = a.id
WHERE o.is_deleted = 0
  AND o._fivetran_active = 1
  AND oli.is_deleted = 0
  AND oli._fivetran_active = 1
  AND p.is_deleted = 0
  AND p._fivetran_active = 1
  AND a.is_deleted = 0
  AND a._fivetran_active = 1
  AND o.stage_name = 'Closed Booked'
  AND a.name ILIKE '%Vodafone%';
```

**Query Interpretation Guide:**
- **"Unique Deals"**: `COUNT(DISTINCT o.id)` - How many separate opportunities involved this product
- **"Total Line Items"**: `COUNT(*)` - Total purchase transactions (same opportunity can have multiple line items)
- **"Total Quantity"**: `SUM(oli.quantity)` - Actual volume purchased (licenses, nodes, etc.)

**Natural Language Query**: "Give me a complete summary on Vodafone's historical buying behaviours, Route to Market, product line, product name and what spend?"
```sql
SELECT
    a.name AS "Account Name",
    o.close_date AS "Close Date",
    o.fulfillment_channel_c AS "Route to Market",
    p.product_line_c AS "Product Line",
    p.name AS "Product Name",
    oli.quantity AS "Quantity",
    oli.total_price AS "Line Item Amount",
    o.amount AS "Opportunity Amount",
    o.currency_iso_code AS "Currency"
FROM SFSALESLEGACY_DB.SFSALES_MARTS.SFSALES_OPPORTUNITY o
JOIN SFSALESLEGACY_DB.GENERAL_MARTS.GENERAL_ACCOUNT a ON o.account_id = a.id
JOIN SFSALESLEGACY_DB.SFSALES_MARTS.SFSALES_OPPORTUNITY_LINE_ITEM oli ON oli.opportunity_id = o.id
JOIN SFSALESLEGACY_DB.SFSALES_MARTS.SFSALES_PRODUCT p ON oli.product_2_id = p.id
WHERE o.stage_name = 'Closed Booked'
  AND o.close_date > ADD_MONTHS(CURRENT_DATE, -120)  -- Last 10 years for "historical"
  AND o.is_deleted = 0
  AND o._fivetran_active = 1
  AND a.is_deleted = 0
  AND a._fivetran_active = 1
  AND oli.is_deleted = 0
  AND oli._fivetran_active = 1
  AND p.is_deleted = 0
  AND p._fivetran_active = 1
  AND a.name ILIKE '%Vodafone%'
ORDER BY o.close_date DESC
LIMIT 20;
```

**Natural Language Query**: "Find 9 most recent booked overlay credit opps for Vodafone, and give the aggregate sum of amount in USD"
```sql
SELECT
    a.name AS "Account Name",
    o.opportunity_number_c AS "Opportunity Number",
    o.close_date AS "Close Date",
    o.stage_name AS "Stage",
    o.opportunity_type_c AS "Opportunity Type",
    o.amount AS "Amount",
    o.currency_iso_code AS "Currency",
    o.name AS "Opportunity Name"
FROM SFSALESLEGACY_DB.SFSALES_MARTS.SFSALES_OPPORTUNITY o
JOIN SFSALESLEGACY_DB.GENERAL_MARTS.GENERAL_ACCOUNT a ON o.account_id = a.id
WHERE a.name ILIKE '%Vodafone%'
    AND o.opportunity_type_c = 'Overlay Credit'  -- More reliable than type field
    AND o.stage_name = 'Closed Booked'
    AND o.is_deleted = 0
    AND o._fivetran_active = 1
    AND a.is_deleted = 0
    AND a._fivetran_active = 1
ORDER BY o.close_date DESC
LIMIT 9;

-- Aggregate summary
SELECT
    COUNT(*) AS "Number of Opportunities",
    SUM(o.amount_for_skuid_c) AS "Total Amount USD (Converted)"
FROM SFSALESLEGACY_DB.SFSALES_MARTS.SFSALES_OPPORTUNITY o
JOIN SFSALESLEGACY_DB.GENERAL_MARTS.GENERAL_ACCOUNT a ON o.account_id = a.id
WHERE a.name ILIKE '%Vodafone%'
    AND o.opportunity_type_c = 'Overlay Credit'
    AND o.stage_name = 'Closed Booked'
    AND o.is_deleted = 0
    AND o._fivetran_active = 1
    AND a.is_deleted = 0
    AND a._fivetran_active = 1
ORDER BY o.close_date DESC
LIMIT 9;
```

**Natural Language Query**: "What is the breakout of sales to the DHL account from Jan 2024 through Jul 2025 by region? what is the total amount for APAC region?"
```sql
-- Regional sales analysis using proper geographic field hierarchy
WITH dhl_regional_sales AS (
    SELECT
        o.super_region_c AS "Super Region",
        o.region_c AS "Region",
        COUNT(DISTINCT o.id) AS "Opportunities",
        SUM(o.amount_for_skuid_c) AS "Total Amount (USD Converted)",
        COUNT(DISTINCT o.currency_iso_code) AS "Currency Types"
    FROM SFSALESLEGACY_DB.SFSALES_MARTS.SFSALES_OPPORTUNITY o
    JOIN SFSALESLEGACY_DB.GENERAL_MARTS.GENERAL_ACCOUNT a ON o.account_id = a.id
    WHERE a.name ILIKE '%DHL%'
        AND o.stage_name = 'Closed Booked'
        AND o.close_date >= '2024-01-01'
        AND o.close_date <= '2025-07-31'
        AND o.is_deleted = 0
        AND o._fivetran_active = 1
        AND a.is_deleted = 0
        AND a._fivetran_active = 1
    GROUP BY o.super_region_c, o.region_c
)
SELECT * FROM dhl_regional_sales
ORDER BY "Total Amount (USD)" DESC;

-- APAC region specific total example
SELECT
    'APAC Total' AS "Summary",
    COUNT(DISTINCT o.id) AS "APAC Opportunities",
    SUM(o.amount_for_skuid_c) AS "APAC Total Amount (USD Converted)"
FROM SFSALESLEGACY_DB.SFSALES_MARTS.SFSALES_OPPORTUNITY o
JOIN SFSALESLEGACY_DB.GENERAL_MARTS.GENERAL_ACCOUNT a ON o.account_id = a.id
WHERE a.name ILIKE '%DHL%'
    AND o.super_region_c = 'APAC'  -- Use super_region_c for clean regional filtering
    AND o.stage_name = 'Closed Booked'
    AND o.close_date >= '2024-01-01'
    AND o.close_date <= '2025-07-31'
    AND o.is_deleted = 0
    AND o._fivetran_active = 1
    AND a.is_deleted = 0
    AND a._fivetran_active = 1;
```

**Natural Language Query**: "What are the historical partners that Vodafone has transacted business through for Red Hat Products?"
```sql
  SELECT
    pa.name AS "Partner Account",
    count(op.id) AS "Number of Booked Opps"
FROM SFSALESLEGACY_DB.GENERAL_MARTS.GENERAL_OPPORTUNITY o
JOIN SFSALESLEGACY_DB.GENERAL_MARTS.GENERAL_OPPORTUNITY_PARTNER op ON op.opportunity_c = o.id
JOIN SFSALESLEGACY_DB.GENERAL_MARTS.GENERAL_ACCOUNT pa ON op.partner_c = pa.id
JOIN SFSALESLEGACY_DB.GENERAL_MARTS.GENERAL_ACCOUNT oa ON o.account_id = oa.id
WHERE o._fivetran_active = true
  AND op._fivetran_active = true
  AND pa._fivetran_active = true
  AND oa._fivetran_active = true
    AND oa.name ILIKE '%Vodafone%'
  AND o.stage_name = 'Closed Booked'
  AND o.close_date > add_months(current_date, -120)
  GROUP BY pa.name
  ORDER BY count(op.id) DESC;
```

**Natural Language Query**: "Based on legacy data, give me a complete summary on Vodafone's historical buying behaviours, Route to Market, what products and what spend etc?"
```sql
  SELECT
    a.name AS "Account Name",
    o.fulfillment_channel_c AS "Route to Market",
    o.close_date AS "Opp Close Date",
    p.product_line_c AS "Product Line",
    p.name AS "Product Name",
    oli.quantity
FROM SFSALESLEGACY_DB.GENERAL_MARTS.GENERAL_OPPORTUNITY o
JOIN SFSALESLEGACY_DB.GENERAL_MARTS.GENERAL_ACCOUNT a ON o.account_id = a.id
JOIN SFSALESLEGACY_DB.GENERAL_MARTS.GENERAL_OPPORTUNITY_LINE_ITEM oli ON oli.opportunity_id = o.id
JOIN SFSALESLEGACY_DB.GENERAL_MARTS.GENERAL_PRODUCT p ON oli.product_2_id = p.id
WHERE o.stage_name = 'Closed Booked'
  AND o.close_date > add_months(current_date, -120)
  AND o._fivetran_active = true
  AND a._fivetran_active = true
  AND oli._fivetran_active = true
  AND p._fivetran_active = true
    AND a.name ILIKE '%Vodafone%'
ORDER BY close_date DESC;
```

**Natural Language Query**: "Tell me about the opportunities that Ashlyn Flurry contributed to in 2023 (either owner of or on the opportunity team and only 'Closed Booked')"
```sql
-- Person-specific contribution analysis - Team Member approach (comprehensive)
SELECT
    o.opportunity_number_c AS "Opportunity Number",
    a.name AS "Account Name",
    o.close_date AS "Close Date",
    o.stage_name AS "Stage",
    o.amount_for_skuid_c AS "Amount (USD Converted)",
    o.amount AS "Original Amount",
    o.currency_iso_code AS "Currency"
FROM SFSALESLEGACY_DB.SFSALES_MARTS.SFSALES_OPPORTUNITY o
JOIN SFSALESLEGACY_DB.GENERAL_MARTS.GENERAL_OPPORTUNITY_TEAM_MEMBER otm ON otm.opportunity_id = o.id
JOIN SFSALESLEGACY_DB.SFSALES_MARTS.SFSALES_USER u ON otm.user_id = u.id
JOIN SFSALESLEGACY_DB.GENERAL_MARTS.GENERAL_ACCOUNT a ON o.account_id = a.id
WHERE u.name = 'Ashlyn Flurry'  -- Exact name match for precision
    AND o.stage_name = 'Closed Booked'
    AND o.close_date >= '2023-01-01'
    AND o.close_date < '2024-01-01'
    AND o.is_deleted = 0
    AND o._fivetran_active = 1
    AND otm._fivetran_active = 1
    AND u._fivetran_active = 1
    AND a.is_deleted = 0
    AND a._fivetran_active = 1
ORDER BY o.close_date DESC;

-- Alternative: Owner-only approach (focused)
SELECT
    o.opportunity_number_c AS "Opportunity Number",
    a.name AS "Account Name",
    o.close_date AS "Close Date",
    o.amount_for_skuid_c AS "Amount (USD Converted)",
    o.currency_iso_code AS "Currency"
FROM SFSALESLEGACY_DB.SFSALES_MARTS.SFSALES_OPPORTUNITY o
JOIN SFSALESLEGACY_DB.SFSALES_MARTS.SFSALES_USER u ON o.owner_id = u.id
JOIN SFSALESLEGACY_DB.GENERAL_MARTS.GENERAL_ACCOUNT a ON o.account_id = a.id
WHERE u.name = 'Ashlyn Flurry'
    AND o.stage_name = 'Closed Booked'
    AND o.close_date >= '2023-01-01'
    AND o.close_date < '2024-01-01'
    AND o.is_deleted = 0
    AND o._fivetran_active = 1
    AND u._fivetran_active = 1
    AND a.is_deleted = 0
    AND a._fivetran_active = 1
ORDER BY o.close_dat
