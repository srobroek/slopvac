# Why we replaced TTL cache expiry with event-driven invalidation

Our product catalog cache served stale reads to 3.1% of requests under TTL-based expiry. We measured this over a four-week baseline before making any changes. This post describes the switch to event-driven invalidation and the results from the four weeks after rollout.

## The problem with TTL expiry

Our catalog cache stored product records (price, inventory count, title, images) with a fixed TTL of 60 seconds. A write to the catalog database did not touch the cache. The cache entry stayed valid, by definition, until the TTL expired, regardless of whether the underlying data had changed.

This produced a fixed window of staleness on every write. A price change or inventory update could take up to 60 seconds to appear in reads. During that window, some fraction of requests returned old data. Over our four-week baseline, that fraction averaged 3.1% of catalog reads, measured by comparing cache responses against the database of record.

## The change: event-driven invalidation

We connected the catalog write path to a message queue. Every write to the catalog database now publishes an invalidation event containing the product ID and the field that changed. A consumer service reads these events and evicts the corresponding cache key immediately.

The cache no longer relies on a fixed expiry window to bound staleness. Staleness is now bounded by the time between a write and the consumer processing its event, not by a 60-second timer.

We kept a TTL of 24 hours as a backstop, to guard against a missed or dropped invalidation event. Under normal operation, the eviction happens before that TTL would fire.

## Results over four weeks

We ran the new system in production for four weeks and measured the same metrics as the baseline.

- Stale reads fell from 3.1% to 0.04% of catalog read requests.
- p99 read latency stayed unchanged at 41 ms.
- The invalidation queue peaked at 1,200 events per second during a scheduled sale day.

The unchanged p99 latency matters: invalidation runs on the write path and the event consumer, not on the read path, so read performance carries no penalty from the added infrastructure.

The 1,200 events/sec peak occurred during the highest-write-volume event we saw in the four-week window, a scheduled sale with concentrated price and inventory updates. The consumer kept pace with that peak without a backlog.

## What this means for a similar cache

If your cache staleness bound is a fixed TTL, that bound holds even when nothing changed and even when something did. Event-driven invalidation makes the staleness bound track actual writes instead of a timer, at the cost of a message queue and a consumer service on the write path.

## License

MIT
