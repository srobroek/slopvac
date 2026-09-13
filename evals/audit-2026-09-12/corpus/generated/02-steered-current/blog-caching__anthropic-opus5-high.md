# Why we replaced TTL expiry with event-driven invalidation in the catalog cache

Our product catalog cache serves price, availability, and description fields to the storefront and the mobile API. Until 2026-08-10 it expired entries on a 60-second TTL. It now deletes entries when the catalog service publishes a change event, and keeps a 15-minute TTL underneath as a fallback.

Measured over the four weeks from 2026-08-10 to 2026-09-06, against the four weeks from 2026-07-13 to 2026-08-09:

| Metric | 60-second TTL | Event-driven |
| --- | --- | --- |
| Stale reads, share of catalog reads | 3.1% | 0.04% |
| p99 read latency | 41 ms | 41 ms |
| Peak origin fetches per second | 8,100 | 640 |
| Peak invalidation events per second | — | 1,200 |
| p50 invalidation lag, write to key delete | — | 240 ms |
| p99 invalidation lag | — | 1.4 s |

The 1,200 events per second peak occurred on 2026-08-29, a sale day on which merchandising repriced 84,000 SKUs in 90 minutes.

## What the TTL bounded, and what it did not

A 60-second TTL bounds how long one entry can be stale at 60 seconds. It does not bound the share of reads that return stale data, because that share tracks the write rate against the read rate. When merchandising repriced a SKU that the storefront read 400 times per minute, the TTL let roughly 400 reads return the old price.

We measure stale reads by sampling 1 read in 500 in the `catalog-read` middleware, refetching from Postgres, and comparing the two payloads field by field. That sampler reported 3.1% mismatches across the July window, and 6.8% during the 2026-07-25 sale.

## Why we did not shorten the TTL instead

The cache holds 480,000 hot SKU keys in Redis. A 60-second TTL produced 8,100 origin fetches per second at peak. A 5-second TTL would have produced about 96,000 per second, and would have cut stale reads to roughly 0.26% — still six times the 0.04% we now measure.

Our catalog Postgres read replicas sustain 12,000 queries per second at p99 under 25 ms. Above that, p99 crosses 200 ms and the read path starts shedding. So 96,000 fetches per second was not available to us at any TTL, and the staleness floor stayed above 0.2% regardless.

## How invalidation works

1. `catalog-service` writes the SKU row and an outbox row to the `catalog_outbox` table in one Postgres transaction.
2. Debezium 2.7 tails the WAL and publishes each outbox row to the Kafka topic `catalog.changes`, partitioned by SKU.
3. The `cache-invalidator` consumer issues `UNLINK catalog:v3:{sku}` against the Redis cluster.
4. The next read for that SKU misses, fetches from Postgres, and writes the entry back with a 15-minute TTL.

Four properties make this safe to run:

- **Atomicity.** The outbox row commits with the data row, so a committed write always has a pending event.
- **Ordering per key.** Partitioning by SKU keeps events for one SKU in order on one partition, so a stale delete cannot overtake a newer write.
- **Idempotence.** `UNLINK` on an absent key is a no-op, so at-least-once delivery costs nothing.
- **A fallback TTL.** The 15-minute TTL caps staleness when an event is lost, so a broken consumer degrades the cache to a coarse TTL cache rather than serving indefinitely stale data.

## Where the remaining 0.04% comes from

Two sources account for it. Invalidation lag leaves a window of 240 ms at p50 and 1.4 s at p99 in which reads still hit the old entry. Consumer restarts during deploys add a gap of 6 to 9 seconds per rolling restart, and we deploy `cache-invalidator` about 20 times a week.

We have not tried to close that window. Driving it lower means either read-through locking on the write path or a version token threaded through the API, and neither is worth 0.04% to us at present.

## Latency did not move

p99 read latency held at 41 ms across both windows. The read path is unchanged: the same Redis `GET`, the same deserialization, the same Postgres fallback on a miss. Event-driven invalidation changes when a key disappears, not what a read does. Miss rate fell from 1.7% to 0.13%, which is too small a share of requests to shift p99.

## Preconditions we would check first

Before another team makes this swap, five things need to hold:

- Every write that changes cached data emits an event in the same transaction. A write path that bypasses the outbox reintroduces unbounded staleness with no TTL to catch it.
- The cache key is derivable from the event payload alone. Our events carry the SKU, which is the whole key.
- The invalidation operation is idempotent, so redelivery is free.
- A fallback TTL stays in place. Ours is 15 minutes.
- The queue has headroom over the write burst. We load-tested `cache-invalidator` to 10,000 events per second, and the 2026-08-29 sale peaked at 1,200.

If your write path has entry points outside the transactional outbox, fix that before touching the cache. Event-driven invalidation inherits the completeness of the event stream, and a stream that misses writes produces stale entries that nothing shorter than 15 minutes will clear.
