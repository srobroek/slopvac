# Why We Switched Our Product Catalog Cache from TTL Expiry to Event-Driven Invalidation

Our product catalog cache served stale prices and out-of-stock items to 3.1% of requests. TTL expiry couldn't fix that without either shortening the TTL, which raises origin load, or accepting the staleness. We replaced TTL expiry with event-driven invalidation. Over the four weeks that followed, stale reads fell from 3.1% to 0.04% of requests, p99 latency held at 41 ms, and the invalidation queue peaked at 1,200 events per second on a sale day.

## The problem with TTL expiry

Our cache held product records (price, stock count, title, images) with a fixed TTL. A write to the catalog database did not touch the cache. The cache entry stayed valid until the TTL expired, regardless of whether the underlying record had changed.

Under TTL expiry, a price change or stock update took up to the full TTL duration to reach the cache. We measured 3.1% of catalog reads returning a stale record during a four-week baseline period before the switch. Shortening the TTL would reduce staleness but increase the read rate against the origin database in proportion.

## The design: event-driven invalidation

We moved invalidation to the write path. Every write to the catalog database (price update, stock adjustment, product edit) now publishes an invalidation event carrying the product ID. A consumer service reads the event stream and deletes the corresponding cache entry. The next read for that product ID misses the cache and repopulates it from the origin database with the current record.

The cache entries carry no expiry. A product ID stays cached until a write to that product ID triggers an invalidation event.

## Results after four weeks

We ran the new system in production for four weeks and measured three figures against the same metrics from the TTL-based baseline:

- Stale reads: 3.1% of requests before, 0.04% of requests after.
- p99 read latency: 41 ms before, 41 ms after, unchanged.
- Invalidation queue throughput: peaked at 1,200 events per second on a sale day.

The stale-read reduction came from removing the TTL window entirely: a cache entry now reflects the last write to that record, not the last write within a TTL-bounded lookback. The unchanged p99 latency means the added invalidation-consumer step did not shift the tail of the read-path latency distribution. The 1,200-events-per-second peak occurred on a sale day, when concurrent stock and price updates across the catalog spiked the write volume.

## What to check before adopting this pattern

Event-driven invalidation depends on the write path publishing an invalidation event for every write that changes a cached field. A write path that bypasses the event publisher (a direct database migration, a bulk import script) will leave a stale cache entry with no TTL to eventually expire it. Audit every write path to the catalog database before removing TTL as a fallback.

The invalidation consumer needs enough throughput to handle write bursts. Our peak of 1,200 events per second occurred during a sale event; size the consumer's processing capacity against your own peak write volume, not just steady-state traffic.
