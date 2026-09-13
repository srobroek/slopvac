# Replacing TTL expiry with event-driven invalidation in the product catalog cache

Our catalog service serves product records from Redis and reads through to Postgres on a miss. Until 2026-08-16 each cache entry expired on a 300-second TTL. Since 2026-08-16 the cache deletes an entry when Postgres commits a change to the underlying row.

Over the four weeks from 2026-08-16 to 2026-09-13, stale reads fell from 3.1% to 0.04% of catalog read requests. Read latency at p99 stayed at 41 ms. The invalidation queue peaked at 1,200 events per second on the 2026-08-29 sale day.

## How we measure a stale read

Every cache entry stores the `row_version` of the Postgres row it was built from. A sampler takes 1 request in 500, re-reads `products.row_version` for the served product ID, and records a mismatch as a stale read. Under the 300-second TTL that sampler reported 3.1% mismatches across the four weeks before the change.

Most of those mismatches were price and availability edits made by merchandisers, who then reloaded a product page and saw the old price. Each report cost a support ticket and an engineer's reply saying to wait five minutes.

## Why we did not shorten the TTL

Under TTL expiry the worst-case stale window equals the TTL, so cutting staleness means cutting the TTL. Catalog reads peak at 12,000 requests per second with a 99.2% cache hit ratio, which sends about 96 reads per second to the Postgres primary.

We load-tested a 30-second TTL against a production-sized dataset. Origin reads rose to 940 per second and read p99 rose from 41 ms to 88 ms. Our latency budget for the catalog read path is 50 ms at p99, so a 30-second TTL was not available to us.

## The invalidation path

The pipeline has four stages:

1. Postgres logical replication publishes row changes on the `products` and `product_prices` tables.
2. Debezium 2.7 converts each change into a Kafka record keyed by product ID, on the topic `catalog.changes`.
3. The invalidator consumer group reads that topic and issues `DEL catalog:v3:<product_id>` against Redis.
4. The next read for that product ID misses, reads Postgres, and writes a fresh entry.

The invalidator deletes rather than writes the new value. A change event carries the changed row alone, and a cache entry joins six tables including live inventory, so the invalidator cannot assemble a correct entry from the event.

## Ordering and late writes

Keying `catalog.changes` by product ID puts every event for one product in one partition, so one consumer processes that product's changes in commit order. Ordering across products does not matter, because each cache key covers one product.

Ordering inside a partition does not stop a slow reader from writing a stale entry after the delete. A read that started before the commit can finish after it. The cache write path therefore compares `row_version` and rejects any write whose version is lower than the version already stored. That guard rejected 1,431 writes over the four weeks.

Lost events remain possible when a Debezium connector restarts past a retention boundary. Each entry keeps a 24-hour fallback TTL, which bounds staleness at 24 hours if the event never arrives. The fallback TTL fired on 0.8% of entries during the four weeks, because normal invalidation removed the rest first.

## Measured results

| Metric | 300-second TTL (four weeks to 2026-08-16) | Event-driven (four weeks to 2026-09-13) |
| --- | --- | --- |
| Stale reads, sampled | 3.1% of requests | 0.04% of requests |
| Read p99 | 41 ms | 41 ms |
| Postgres origin reads, peak | 96/s | 88/s |
| Cache hit ratio | 99.2% | 99.3% |
| Invalidation events, peak | not applicable | 1,200/s |

Latency did not move, because the read path is unchanged. The change replaced what removes an entry, not what happens on a hit or a miss.

The 1,200 events per second peak on 2026-08-29 came from a bulk price update across 41,000 SKUs. One invalidator pod handles 4,000 events per second in our load tests, and the group runs three pods, so that peak consumed 10% of provisioned capacity. Consumer lag reached 8,400 events for 22 seconds during the peak and then returned to under 50.

## What the remaining 0.04% is

The residual stale reads fall inside the window between the Postgres commit and the Redis delete. We measure that window from the commit timestamp in the change event to the acknowledged `DEL`. The median is 90 ms and p99 is 420 ms. During the 2026-08-29 peak p99 reached 1.4 s.

Closing that window further requires invalidating inside the write transaction, which couples catalog writes to Redis availability. We hold the 90 ms median instead.

## What the change cost

The team now operates a Kafka topic, a Debezium connector, and a three-pod consumer group that did not exist under the TTL design. Three alerts page on this path: consumer lag above 5,000 events for 60 seconds, connector replication slot lag above 1 GB, and fallback-TTL expiries above 5% of entries per hour. The replication slot adds write-ahead log retention on the Postgres primary, which we cap at 4 GB.

A deployment that stops the invalidator does not break reads. Staleness degrades toward the 24-hour fallback TTL until the consumer group catches up.

## Configuration

| Name | Type | Default | Effect |
| --- | --- | --- | --- |
| `CATALOG_CACHE_FALLBACK_TTL` | duration | `24h` | Upper bound on staleness when an invalidation event never arrives |
| `CATALOG_CACHE_VERSION_GUARD` | bool | `true` | Rejects a cache write whose `row_version` is lower than the stored version |
| `CATALOG_INVALIDATOR_PARTITIONS` | int | `12` | Partition count on `catalog.changes`, and the ceiling on consumer parallelism |
| `CATALOG_INVALIDATOR_MAX_LAG_EVENTS` | int | `5000` | Consumer lag that triggers the paging alert |
| `CATALOG_CACHE_KEY_PREFIX` | string | `catalog:v3` | Key namespace, bumped to invalidate every entry at once |

Set `CATALOG_CACHE_FALLBACK_TTL` to a value your operators accept as a worst case. A shorter fallback TTL raises origin reads by the same arithmetic that ruled out a 30-second TTL for us.
