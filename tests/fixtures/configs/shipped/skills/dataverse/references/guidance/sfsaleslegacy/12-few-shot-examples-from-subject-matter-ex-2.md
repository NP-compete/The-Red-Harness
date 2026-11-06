<!-- sfsaleslegacy · from 04-few-shot-examples-from-subject-matter-ex-2.md -->
e DESC;

-- Grand Total Summary for Ashlyn Flurry's 2023 "Closed Booked" Opportunities
SELECT
    COUNT(*) AS "Total Opportunities",
    SUM(o.amount_for_skuid_c) AS "Grand Total (USD Converted)",
    SUM(CASE WHEN otm.team_member_role = 'Opportunity Owner' THEN o.amount_for_skuid_c ELSE 0 END) AS "Total as Owner",
    SUM(CASE WHEN otm.team_member_role = 'Inside Rep' THEN o.amount_for_skuid_c ELSE 0 END) AS "Total as Inside Rep",
    SUM(CASE WHEN otm.team_member_role = 'Back-Up' THEN o.amount_for_skuid_c ELSE 0 END) AS "Total as Back-Up",
    MIN(o.close_date) AS "First Close Date",
    MAX(o.close_date) AS "Last Close Date"
FROM SFSALESLEGACY_DB.SFSALES_MARTS.SFSALES_OPPORTUNITY o
JOIN SFSALESLEGACY_DB.GENERAL_MARTS.GENERAL_OPPORTUNITY_TEAM_MEMBER otm ON otm.opportunity_id = o.id
JOIN SFSALESLEGACY_DB.SFSALES_MARTS.SFSALES_USER u ON otm.user_id = u.id
JOIN SFSALESLEGACY_DB.GENERAL_MARTS.GENERAL_ACCOUNT a ON o.account_id = a.id
WHERE u.name = 'Ashlyn Flurry'
    AND o.stage_name = 'Closed Booked'
    AND o.close_date >= '2023-01-01'
    AND o.close_date < '2024-01-01';
```
**Query Choice Guide:**
- **Team Member Approach**: More comprehensive (354 opportunities, $746.5M) - includes all contribution types (Owner, Inside Rep, Back-Up, etc.)
- **Owner-Only Approach**: Focused view (316 opportunities, $725.4M) - direct ownership only
- **⚠️ Avoid UNION**: Combining approaches causes role-based duplicates - same opportunity counted multiple times with different role labels, inflating totals to $1.47B+ instead of correct $746.5M
- **Exact Name Matching**: Use `u.name = 'Exact Name'` instead of `ILIKE '%Name%'` for precise person identification

**Natural Language Query**: "What are the historical partners that Vodafone has transacted business through for Red Hat Products? what is the total number of booked opps in last ten years?"
```sql
-- Partner relationship analysis - counts all partner-opportunity relationships
SELECT
    pa.name AS "Partner Account",
    COUNT(op.id) AS "Number of Partner Relationships"
FROM SFSALESLEGACY_DB.GENERAL_MARTS.GENERAL_OPPORTUNITY o
JOIN SFSALESLEGACY_DB.GENERAL_MARTS.GENERAL_OPPORTUNITY_PARTNER op ON op.opportunity_c = o.id
JOIN SFSALESLEGACY_DB.GENERAL_MARTS.GENERAL_ACCOUNT pa ON op.partner_c = pa.id
JOIN SFSALESLEGACY_DB.GENERAL_MARTS.GENERAL_ACCOUNT oa ON o.account_id = oa.id
WHERE o.is_deleted = 0
  AND o._fivetran_active = 1
  AND op.is_deleted = 0
  AND op._fivetran_active = 1
  AND pa.is_deleted = 0
  AND pa._fivetran_active = 1
  AND oa.is_deleted = 0
  AND oa._fivetran_active = 1
  AND oa.name ILIKE '%Vodafone%'
  AND o.stage_name = 'Closed Booked'
  AND o.close_date >= ADD_MONTHS(CURRENT_DATE, -120)
GROUP BY pa.name
ORDER BY COUNT(op.id) DESC;

-- Summary totals
SELECT
    'Total Summary' AS "Analysis",
    COUNT(DISTINCT o.id) AS "Unique Opportunities",
    COUNT(op.id) AS "Total Partner Relationships",
    COUNT(DISTINCT pa.name) AS "Unique Partners",
    ROUND(COUNT(op.id) * 1.0 / COUNT(DISTINCT o.id), 2) AS "Avg Partners Per Opportunity"
FROM SFSALESLEGACY_DB.GENERAL_MARTS.GENERAL_OPPORTUNITY o
JOIN SFSALESLEGACY_DB.GENERAL_MARTS.GENERAL_OPPORTUNITY_PARTNER op ON op.opportunity_c = o.id
JOIN SFSALESLEGACY_DB.GENERAL_MARTS.GENERAL_ACCOUNT pa ON op.partner_c = pa.id
JOIN SFSALESLEGACY_DB.GENERAL_MARTS.GENERAL_ACCOUNT oa ON o.account_id = oa.id
WHERE o.is_deleted = 0
  AND o._fivetran_active = 1
  AND op.is_deleted = 0
  AND op._fivetran_active = 1
  AND pa.is_deleted = 0
  AND pa._fivetran_active = 1
  AND oa.is_deleted = 0
  AND oa._fivetran_active = 1
  AND oa.name ILIKE '%Vodafone%'
  AND o.stage_name = 'Closed Booked'
  AND o.close_date >= ADD_MONTHS(CURRENT_DATE, -120);
```

**Expected Results Pattern**:
- Partner relationships (2,793) > Unique opportunities (1,968) due to multi-partner deals
- Average 1.42 partners per opportunity for enterprise customers
- Top partners: Amazon EU (154), Precision Infomatic (126), IBM India (123)
- Validates partner ecosystem complexity in enterprise sales

**Natural Language Query**: "What payment terms have we given Vodafone and what's the total value of those deals?"
```sql
-- CRITICAL: Payment terms analysis requires GENERAL_CREDIT table, not opportunity fields
-- This query demonstrates proper credit processing workflow integration
SELECT
    c.payment_terms AS "Payment Terms",
    COUNT(DISTINCT o.id) AS "Number of Opportunities",
    SUM(o.amount_for_skuid_c) AS "Total Amount (USD Converted)",
    COUNT(CASE WHEN o.amount_for_skuid_c IS NOT NULL THEN 1 END) AS "Opportunities with USD Amount",
    COUNT(CASE WHEN o.amount_for_skuid_c IS NULL THEN 1 END) AS "Opportunities with NULL USD Amount"
FROM SFSALESLEGACY_DB.GENERAL_MARTS.GENERAL_OPPORTUNITY o
JOIN SFSALESLEGACY_DB.GENERAL_MARTS.GENERAL_ACCOUNT a ON o.account_id = a.id
LEFT OUTER JOIN
    (SELECT opportunity, credit_stage, payment_terms, created_date
     FROM SFSALESLEGACY_DB.GENERAL_MARTS.GENERAL_CREDIT
     WHERE credit_stage LIKE 'Approved%'
       AND _fivetran_active = 1
     QUALIFY ROW_NUMBER() OVER (PARTITION BY opportunity ORDER BY created_date DESC) = 1) c
  ON c.opportunity = o.id
WHERE o.stage_name = 'Closed Booked'
    AND o.close_date > ADD_MONTHS(CURRENT_DATE, -120)
    AND o._fivetran_active = 1
    AND o.is_deleted = 0
    AND a._fivetran_active = 1
    AND a.is_deleted = 0
    AND a.name ILIKE '%Vodafone%'
    AND c.payment_terms IS NOT NULL
GROUP BY c.payment_terms
ORDER BY SUM(o.amount_for_skuid_c) DESC;
```

**Critical Architecture Insights:**
- **Why GENERAL_CREDIT**: Payment terms are managed through credit approval workflows, not stored directly on opportunities
- **Business Process**: Credit records contain the authoritative payment terms after approval process
- **Temporal Logic**: `QUALIFY ROW_NUMBER()` gets the most recent credit decision per opportunity
- **Comprehensive Coverage**: This approach captures 1,620 opportunities (~$91.7M) vs 57 opportunities (~$1.05M) using opportunity fields directly
- **GENERAL_MARTS Requirement**: Only mart with GENERAL_CREDIT table for complete payment terms analysis
