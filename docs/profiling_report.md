# Source Profiling Report

## 1. Source Inventory

| Source | Type | Rows/Records | Key | Update Pattern | Quality Findings |
|---|---|---:|---|---|---|
| customers.csv | CSV file | 250 | customer_id | Full snapshot, ad hoc refresh | 4 exact duplicate rows; 3 duplicate customer_id values; 3 missing emails; 2 missing cities |
| orders.json | JSON file | 250 | order_id | Full snapshot, ad hoc refresh | Nested `shipping` object requires flattening; possible missing keys |
| products.parquet | Parquet file | 200 | product_id | Full snapshot, ad hoc refresh | No material quality issues observed; typed columns preserved by format |
| REST API events | Paginated REST API | 122 (total across all pages) | event_id | Incremental via `updated_after` watermark | 2 repeated event_id values, each with a newer updated_at representing an update |
| support_tickets (PostgreSQL) | PostgreSQL table | 250 | ticket_id | Row-level updates; CDC/timestamp strategy not yet implemented | 4 rows with null assigned_agent |

## 2. Schema Findings

**customers.csv** — 7 columns, all read as string/text type: `customer_id`, `first_name`, `last_name`, `email`, `city`, `signup_date`, `customer_segment`. `signup_date` arrives as plain text but logically represents a calendar date.

**orders.json** — Root structure is a list of records. Top-level keys include order identifiers, dates, and numeric amount fields, plus one nested field: `shipping`, which is a nested object (e.g. address-related sub-fields). The nested object can either be flattened into top-level columns downstream or kept as a nested/struct column, depending on the consumer's needs.

**products.parquet** — Columns preserve their exact types on read (no re-inference needed, unlike CSV/JSON), with a mix of categorical (e.g. category/name fields) and numeric (e.g. price) columns.

**REST API events** — Each page returns `page`, `per_page`, `total`, `has_more`, `next_page`, and an `items` list. Each item includes `event_id` (string), `updated_at` (ISO-8601 timestamp text), `amount` (numeric), and a nested `metadata` object (e.g. `channel`, `campaign`).

**support_tickets** — Includes `ticket_id` as the primary key, an `assigned_agent` column that allows nulls, and timestamp columns for creation/tracking.

## 3. Data Quality Findings

1. `customers.csv` contains 4 exact duplicate rows and 3 duplicate `customer_id` values, meaning the key is not currently unique in the raw source even though it is the intended business key.
2. `customers.csv` has 3 missing `email` values and 2 missing `city` values.
3. `orders.json`'s nested `shipping` object means a flattening or parsing decision must be made before this field can be used in flat, tabular analysis.
4. The REST API deliberately returns 2 duplicate `event_id` values, each with a newer `updated_at`, meaning naive ingestion without deduplication logic would create logical duplicates.
5. `support_tickets` has 4 rows with a null `assigned_agent`, meaning not all tickets currently have an owner.

## 4. Recommended Acquisition Method

| Source | Method |
|---|---|
| customers.csv / orders.json / products.parquet | File copy into `raw/files/`, with a SHA-256 hash manifest to avoid re-copying unchanged content on rerun |
| REST API events | Paginated GET requests, looping until `has_more` is false, with event_id + updated_at deduplication and a persisted `updated_after` watermark for incremental pulls |
| support_tickets (PostgreSQL) | Bounded, read-only inspection queries only in this lab (no full-table scans); a future incremental extraction would need a timestamp or CDC-based strategy |

## 5. Risks and Assumptions

- **Risk:** Treating `customer_id` as guaranteed unique in downstream logic would be incorrect, since the raw source currently contains duplicate keys. Any code relying on uniqueness must handle or flag this rather than assume it.
- **Risk:** Using `event_id` alone to deduplicate API records would silently keep the wrong (stale) version of an event, since the source intentionally repeats IDs with newer timestamps.
- **Risk:** Watermark-based incremental pulls could miss records that share the exact same `updated_at` timestamp as the current watermark, due to the strict "greater than" comparison.
- **Assumption:** The customer, order, and product sources are delivered as full snapshots rather than incremental feeds, since no reliable update timestamp or CDC signal is available for them.
- **Assumption:** The local REST API and PostgreSQL instance used in this lab are stand-ins for real operational systems; the same bounded-query and pagination principles would apply to production equivalents, but with real-world throughput and rate-limit constraints.