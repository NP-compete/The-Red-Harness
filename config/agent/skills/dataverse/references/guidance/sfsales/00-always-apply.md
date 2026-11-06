<!-- sfsales · the rules that apply to every query here -->
# Always apply — sfsales

Read this before writing any SQL for this product. Everything
below applies regardless of what the question asks.

## 🚨 Common Pitfalls & Solutions

| Problem | Solution |
|---------|----------|
| **Including deleted records** | Always filter `is_deleted = false` |
| **Currency confusion** | Specify currency fields and conversion requirements |
| **Stage probability mismatch** | Validate stage/probability alignment with business rules |
| **Double-counting revenue** | Use DISTINCT appropriately, understand opportunity vs product level |
| **Forecast period errors** | Use proper fiscal year/quarter fields, not calendar dates |
| **Territory double-counting** | Handle account team members and territory overlaps carefully |
