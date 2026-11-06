<!-- fammatrix · from 01-quick-start.md -->
## 🚀 QUICK START
**Database:** `fammatrix_db`
**Schema:** `marts`
**Table:** `CONSOLIDATEDLIST` (618 rows)
**Primary Key:** `COSTCENTER` (format: CC###, e.g., CC871)
**Purpose:** Financial accountability mapping and cost center organizational structure

---

## 🎯 SINGLE TABLE RULE

**✅ USE ONLY:** `fammatrix_db.marts.CONSOLIDATEDLIST` for ALL queries
**❌ NEVER USE:** SUPPORTMATRIX table (deprecated)

---

## 🔑 CRITICAL QUERY PRINCIPLES

### ⚠️ EXACT MATCH REQUIREMENTS
- **Match expected columns EXACTLY** when pattern specifies them
- **Get the WHERE clause right** - this is what matters most
- **NO extra columns** for queries with specific patterns (FAM, External Reporting)
- **NO WHERE clause** for "show all" queries unless pattern shows it
- **Keep filters simple and precise** - avoid unnecessary complexity
