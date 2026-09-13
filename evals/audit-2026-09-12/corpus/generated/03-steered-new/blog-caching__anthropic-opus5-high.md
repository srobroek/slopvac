# From TTL expiry to event-driven cache invalidation in the product catalog

On 2026-08-16 our team replaced the 60-second TTL on the product catalog cache with invalidation events published by the catalog service. Over the 28 days that followed, stale reads fell from 3.1% to 0.04% of sampled storefront reads. This post gives the measurement definition, the design, and the numbers.

## What the TTL path did

The catalog cache is a 6-shard Redis cluster in front of the catalog Postgres primary. Storefront reads hit keys of the form `catalog:sku:{sku}`. Each key carried a 60-second TTL.

A price or availability change committed to Postgres stayed invisible to storefront readers until the key expired. That put the median exposure at 30 seconds and the worst case at 60 seconds. Across 38 million catalog reads per day, the sampler recorded 3.1% of reads serving a version older than the committed one.

Shortening the TTL trades staleness for origin load. In a canary on 2026-07-21 we set the TTL to 5 seconds on one shard. Read load on the catalog primary rose from 900 to 7,400 queries per second, and stale reads fell only to 0.9%. A TTL short enough to reach single-digit-basis-point staleness would have needed roughly 12 times the origin capacity we had.

## How we count a stale read

Every catalog row carries a `version` column that the writing transaction increments. Each cached entry stores the version it was built from.

A sampler on 1% of storefront reads compares the served version against the committed version in Postgres at read time. A served version lower than the committed version counts as one stale read. The sampler code did not change across the switch, so the 3.1% and the 0.04% come from the same definition and the same sampling rate.

## The invalidation path

1. The catalog service writes the row and appends the SKU plus the new version to an outbox table in the same transaction.
2. A relay process tails the outbox and publishes one event per SKU to the Kafka topic `catalog.invalidations`, which has 12 partitions keyed by SKU.
3. Four consumer pods read the topic and issue `DEL` for the affected cache keys.
4. The next storefront read misses, loads the row from Postgres, and writes the entry back with the new version.

Keying by SKU puts every event for one SKU on one partition. A consumer therefore observes that SKU's changes in commit order.

## Ordering, duplicates, and lost events

Deleting a key twice has the same effect as deleting it once, so at-least-once delivery needs no deduplication. Ordering between different SKUs does not affect correctness, because each key is independent.

One race needed a guard. A read that started before an invalidation can finish after it and write back the older row. The cache write now replaces an entry only when the incoming version is higher than the stored version, which drops the late write.

We kept a TTL of 6 hours on every key as a bound on a dropped event. Between 2026-08-16 and 2026-09-12, 41 events reached the dead-letter topic after deserialization failures, covering 39 distinct SKUs. Without the 6-hour ceiling, those keys would have served stale data until their next write.

## Results, 2026-08-16 to 2026-09-12

| Metric | 28 days on TTL | 28 days on events |
| --- | --- | --- |
| Stale reads (1% sample) | 3.1% | 0.04% |
| p99 storefront read latency | 41 ms | 41 ms |
| Catalog primary read load | 900 queries/s | 310 queries/s |
| Invalidation events, peak | not applicable | 1,200 events/s |

Read latency held at 41 ms because the read path did not change. Invalidation runs out of band, and the consumers added 1,200 `DEL` commands per second at peak to a cluster already serving 44,000 operations per second.

Origin read load dropped to 310 queries per second because misses now follow writes rather than the clock. Under the 60-second TTL, every actively read SKU refilled once per minute whether or not it had changed.

The sale on 2026-08-29 produced the 1,200 events per second peak, against a steady-state rate of 95 events per second. Consumer lag peaked at 2.4 seconds during that hour. We attribute most of the residual 0.04% to that lag window, which covered about 425,000 stale reads across the 1.06 billion reads in the 28 days.

## What the change did not fix

The first reader after each write pays a cache miss. That miss costs 11 ms at p50 against Postgres and is already inside the 41 ms p99 figure.

Staleness is now bounded by consumer lag instead of by a 60-second timer. A stalled consumer therefore becomes a correctness problem rather than a load problem, and the 6-hour TTL is a weak backstop. We page on consumer group lag above 5 seconds for 2 minutes.

The outbox relay is a single writer per shard. When it restarts, publication pauses for the 3 to 6 seconds the new process needs to acquire the advisory lock and resume from the last committed offset.

## Settings in production

| Setting | Value | Effect |
| --- | --- | --- |
| `catalog.cache.ttl` | 6h | Upper bound on staleness when an event is lost |
| `catalog.invalidations` partitions | 12 | Per-SKU ordering, headroom to 1,200 events/s |
| Consumer pods | 4 | Held lag under 2.4 s at the 1,200 events/s peak |
| Consumer lag alert | 5 s for 2 min | Pages the on-call engineer |
| Write-back version guard | enabled | Drops a late write carrying an older version |
