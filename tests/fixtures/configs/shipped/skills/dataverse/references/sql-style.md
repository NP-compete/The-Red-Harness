### Writing and fixing warehouse SQL

Snowflake. Correct and immediately executable, no placeholders.

- **Never alter a user-provided identifier, name or search term.** Use
  the exact string. Wrapping it for substring matching (`%term%`) is
  fine; changing its characters is not.
- **When the user supplies a list** of emails, IDs or names, include
  every one of them verbatim. Do not sample, truncate or summarise it,
  however long it is.
- Filter dates with ranges (`>=` and `<`), never `YEAR()` / `MONTH()`
  on the column — a function on a filtered column stops the warehouse
  using its partitioning.
- Select the columns you need. Never `SELECT *`.
- `ILIKE` for case-insensitive matching, not `UPPER()`/`LOWER()` on a
  column, for the same reason.
- Filter in `WHERE`; `HAVING` only for aggregates.
- `INNER JOIN` unless you actually need the outer rows.
- Aggregate before joining a large table.
- `DATE_TRUNC()` for period grouping.
- Prefer joins to correlated subqueries.
- `LIMIT` on exploratory queries; omit it when the user gave you a list
  to match against and expects all of them back.
- Keep it inside 10 joins, 5 CTEs, 3 levels of subquery. Past that,
  say the question needs narrowing.

## When the statement fails

There is no validator standing between you and the warehouse. The
error message is the feedback, so read it rather than guessing again.

- **Unknown column or table** — you assumed a name. Go back to Atlan
  and look it up; do not try a variation.
- **Ambiguous column** — qualify it with the table alias.
- **Type error** — cast explicitly rather than reshaping the query.
- **Timeout or too much data** — add the filter you left out, or
  aggregate earlier.

**Two corrective attempts, then stop.** A third is almost always the
same mistake in a new arrangement. Say what you tried, what the
warehouse said, and what you would need to know to get further — that
is a more useful answer than a fourth broken statement.

### Data product guardrails

- **Read-only.** Do not create, register, modify or deprecate a data
  product. These are published contracts with consumers attached.
- **Do not describe a product you did not read.** Dataverse,
  Snowflake and Atlan all hold overlapping metadata; answer from the
  one you actually queried and say which.
- **Report ambiguity rather than choosing.** Two products with
  similar names means two, with what distinguishes them.
- **"No consumers listed" is not "no consumers".** The registry knows
  what was registered.
