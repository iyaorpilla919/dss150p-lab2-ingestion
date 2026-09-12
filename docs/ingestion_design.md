# Ingestion Design (Task 2.4 & Task 2.5)

## Task 2.4 - Ingestion design table

| Source | Method | Raw destination | Duplicate key | Incremental state |
|---|---|---|---|---|
| CSV / JSON / Parquet (customers, orders, products) | File copy + manifest | `raw/files/` | File SHA-256 | N/A (full snapshot each run; hash prevents re-copying unchanged content) |
| REST API (events) | Paginated GET | `raw/api/events.jsonl` | `event_id` (highest `updated_at` wins) | `max(updated_at)` persisted in `state/api_watermark.json` |
| PostgreSQL (`support_tickets`) | Inspection only in this lab | N/A | `ticket_id` | Discussed only; no incremental state implemented (see CDC discussion below) |

**PostgreSQL timestamp/CDC discussion:** `support_tickets` is only inspected with bounded, read-only queries in this lab, not ingested. If extended to incremental ingestion, options include (a) a `last_updated_at`-style watermark column combined with a monotonic `ticket_id`/sequence to break timestamp ties, or (b) native CDC via PostgreSQL logical replication/WAL so updates and deletes are captured without polling the table directly, which is safer for an OLTP source under load.

## Task 2.5 - Watermark semantics

**Definition used in this lab:** the API watermark is the greatest successfully persisted `updated_at` value across all currently-held raw records. On the next run, the pipeline sends `updated_after=<watermark>` so the source returns only records updated after that point. The watermark is operational pipeline state (`state/api_watermark.json`), not source data, and is never written back to the source.

**Q: What could go wrong if the watermark is saved before the raw file is successfully written?**
If the watermark advances first and the raw write then fails (crash, disk error, partial write), the pipeline will believe those records were already durably captured. The next run will request `updated_after` the new watermark and will never re-request the records that were actually lost — silent, permanent data loss with no error signal. This is why this pipeline writes the raw file first (atomically) and only advances the watermark after that write succeeds.

**Q: What could go wrong if the source allows multiple records with exactly the same timestamp?**
The filter `updated_at > watermark` is a strict inequality. If several records share the exact timestamp that became the new watermark, and only some of them were captured in the run that set that watermark, the remaining same-timestamp records will never satisfy `updated_at > watermark` on a later run and will be silently skipped forever.

**Limitation of this simplified watermark:** a timestamp-only watermark cannot guarantee exactly-once, complete capture when multiple source records can legitimately share the same `updated_at` value at the boundary — it can only guarantee "no earlier than the watermark," not "all records at the watermark instant were captured."

**Production-grade mitigation:** use a compound/composite cursor instead of a bare timestamp — e.g. `(updated_at, strictly_increasing_id)` or a monotonically increasing sequence/offset/log position. Ordering and filtering on the compound key disambiguates ties at the exact same timestamp.