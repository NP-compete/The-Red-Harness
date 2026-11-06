<!-- sfsaleslegacy · from 04-few-shot-examples-from-subject-matter-ex-2.md -->
### Attachment & Document Lookup Queries

**Natural Language Query**: "Can you give me the attachment ID for order number 12821848 from SFsaleslegacy?"
```sql
-- Finding attachments by order number via Case subject line
-- Order numbers are often embedded in GENERAL_CASE.SUBJECT (especially for Japanese orders: 注番 = order number)
-- Join path: GENERAL_CASE (search SUBJECT for order number) → GENERAL_ATTACHMENT (PARENT_ID = Case ID)
SELECT
    A.ID AS attachment_id,
    A.NAME AS attachment_name,
    A.PARENT_ID,
    A.CONTENT_TYPE,
    A.BODY_LENGTH,
    A.CREATED_DATE,
    A.OWNER_ID,
    A.IS_DELETED,
    C.CASE_NUMBER,
    C.SUBJECT
FROM SFSALESLEGACY_DB.GENERAL_MARTS.GENERAL_ATTACHMENT A
JOIN SFSALESLEGACY_DB.GENERAL_MARTS.GENERAL_CASE C
    ON A.PARENT_ID = C.ID
WHERE C.SUBJECT LIKE '%12821848%'
    AND A._FIVETRAN_ACTIVE = 1
    AND C._FIVETRAN_ACTIVE = 1
ORDER BY A.CREATED_DATE DESC;
```

**Key Architecture Insight - Attachment Lookup by Order Number:**
- **Order numbers are NOT in a structured field** like `ORACLE_ORDER_NUMBER_C` on the opportunity table for all cases
- **Japanese orders** store the order number in the Case `SUBJECT` field (e.g., `注番：12821848-01`)
- **Join path**: `GENERAL_CASE.SUBJECT LIKE '%<order_number>%'` → returns Case IDs → use as `PARENT_ID` in `GENERAL_ATTACHMENT`
- **Salesforce ID prefix `500`** indicates Case records (vs `006` for Opportunities)
- **GENERAL_MARTS required**: Only mart with both `GENERAL_CASE` and `GENERAL_ATTACHMENT` tables
- **Alternative approach** (if Case IDs are already known):
```sql
SELECT
    ID AS attachment_id,
    NAME AS attachment_name,
    PARENT_ID,
    CONTENT_TYPE,
    BODY_LENGTH,
    CREATED_DATE,
    OWNER_ID,
    IS_DELETED
FROM SFSALESLEGACY_DB.GENERAL_MARTS.GENERAL_ATTACHMENT
WHERE PARENT_ID IN ('<case_id_1>', '<case_id_2>')
    AND _FIVETRAN_ACTIVE = 1
ORDER BY CREATED_DATE DESC;
```
