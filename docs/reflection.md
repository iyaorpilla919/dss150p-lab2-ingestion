**REFLECTION**

1. Why should source profiling occur before implementation of ingestion?
I need to understand what the data actually looks like before I write code to handle it. If I skip profiling, I might assume something is true, like a column always having a value, when it is not. Profiling showed me the real column names, the missing values, and the duplicate keys, so I could design my pipeline around the actual data instead of guessing.

2. What is the difference between source event time/updated_at and ingestion time?
`updated_at` tells me when the record actually changed in the source system. `_ingested_at` tells me when my pipeline pulled that record. These are not the same moment. A record could have been updated hours ago but only ingested by my pipeline just now. Keeping both timestamps lets me tell the difference between when something happened and when I found out about it.

3. Why is event_id alone insufficient to decide which duplicate API record to keep in this exercise?
The API can send the same `event_id` more than once, with a newer `updated_at` each time. If I only looked at `event_id`, I would not know which version is the most current one. I have to compare the `updated_at` values for records sharing the same `event_id` and keep the one with the latest timestamp.

4. Why must watermark state advance only after successful persistence?
If I update the watermark before I am sure the data was actually saved, and the save then fails, my pipeline will think it already has that data. On the next run, it will not ask for those records again, and I will lose them permanently without even knowing it. That is why I only update the watermark after I confirm the raw file was written successfully.

5. What limitation does updated_after > watermark have when multiple source records can share exactly the same timestamp?
Since the check is "greater than," any record with the exact same timestamp as my saved watermark will not be picked up next time. If two records share that exact timestamp and only one was captured before I saved the watermark, the other one could be skipped forever.

6. How is duplicate prevention related to idempotency?
Idempotency means that running my pipeline again with the same input should not change the result. Duplicate prevention is what makes that possible. For files, I compare content hashes so I do not copy the same file twice. For API records, I compare `event_id` and `updated_at` so I do not add the same event twice. Without these checks, every rerun would create duplicate data.

7. Why should the raw area preserve source values instead of applying business transformations?
The raw area is meant to be an exact, unedited copy of what the source gave me. If I clean or transform the data at this stage and later find a mistake in my cleaning logic, I would have no original copy to go back to and fix it properly. Keeping the raw data untouched means I can always reprocess it correctly later.

8. How could querying a production OLTP source for profiling or extraction degrade the application?
If I run large, unbounded queries or full table scans against a live production database, I could slow it down for real users, lock rows they need, or use up connections the application relies on. This is why I used small, limited queries, like `SELECT ... LIMIT 10`, instead of pulling the whole table at once.

9. What would you change if the API had a rate limit of 60 requests per minute?
I would add a short delay between each page request so I do not go over the limit. I would also check for a 429 error response and pause before retrying if the server tells me to slow down. Using a larger `per_page` value would also help, since it means fewer requests are needed to get all the data.

10. How would you extend this pipeline from a local raw area to PostgreSQL while preserving rerun safety?
I would load the data into a staging table first, using the same logical key (like `event_id`) to update existing rows instead of inserting duplicates. I would only mark the load as successful and move the watermark forward after the database confirms the data was saved. This keeps the same safety rule I already use: never advance state until the write has actually succeeded.