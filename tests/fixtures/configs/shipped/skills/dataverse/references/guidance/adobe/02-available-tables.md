<!-- adobe · from 01-business-context-domain.md -->
## Available Tables


| Table          | Database.Schema  | Purpose                                                                                                  |
| -------------- | ---------------- | -------------------------------------------------------------------------------------------------------- |
| `adobe_mrktng` | `adobe_db.marts` | Marketing mart – hit-level Adobe Analytics data for marketing analytics, attribution, campaign analytics |


RULE: The adobe_mrktng table is the only table that can be used by AI from this data product.  Never use ADOBE_DB.MARTS.ADOBE_RH_DASH_PORTAL, ADOBE_DB.MARTS.ADOBE_RH_DASH_LAB and ADOBE_DB.MARTS.EVENT_LOOKUP tables.

---

## Critical Rules for adobe_mrktng

### 1. **Primary Key & Identifiers**

- **Primary Key**: `marketing_touchpoint_id` (composite of `_data_file_name` and `_row_index`)
- **Session ID**: `adobe_session_id` = `mcvisid` + `visit_num` (convenience identifier for a visit)
- **Visitor ID**: `mcvisid` – Experience Cloud Visitor ID (128-bit)

### 2. **Excluded Hits**

- `**exclude_hit`**: When > 0, the hit is excluded from Adobe reporting (visit_num not incremented)
- **Recommended**: Filter `exclude_hit = 0`  for standard analytics (unless analyzing excluded hits)

### 3. **hit source**

- `**hit_source`**: hit_source=1 is the default for Adobe reporting
- **Recommended**: Filter `hit_source = 1` for standard analytics

### 4. **Date/Time Columns**

- `**date_day**`: Human-readable hit date (no time) (report suite time zone).  Default to using date_day field for the date in general.
- `**date_time`**: Human-readable hit time (report suite time zone)
- `**_fivetran_synced**`: Fivetran sync timestamp (used for incremental loads)

### 5. **Data Lineage**

- **Source**: Fivetran → `stg_adobe__raw` → `adobe_mrktng`
- **Update Frequency**: Daily
- **Column Names**: Raw Adobe/Fivetran names preserved; no renaming
