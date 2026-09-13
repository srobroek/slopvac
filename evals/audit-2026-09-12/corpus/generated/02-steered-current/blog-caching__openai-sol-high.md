# Replacing TTL Expiry with Event-Driven Cache Invalidation

Our product catalog cache used TTL-based expiry to remove entries after a configured interval. A catalog update could supersede an entry while the cache continued serving its previous value.

That behavior produced stale responses until each affected entry expired. Before the change, stale reads accounted for 3.1% of product catalog requests.

We switched to event-driven invalidation because catalog changes identify when cached data becomes obsolete. The cache no longer waits for elapsed time before removing an affected entry.

## Why TTL tuning was insufficient

TTL tuning trades stale-window duration against expiry frequency. Decreasing the TTL schedules earlier expirations, while increasing it permits superseded entries to remain available longer.

No TTL value connects entry validity to a specific catalog change. A cached product remains valid until its deadline, regardless of catalog writes during that interval.

Our freshness requirement depended on catalog changes rather than entry age. Event-driven invalidation connects those two operations without adding invalidation work to synchronous reads.

## How invalidation works

The catalog processes each update through the following sequence:

1. The catalog service commits the product change.
2. The publisher places an invalidation event on the queue.
3. The consumer removes the affected product from the cache.
4. The next request reloads the product after the resulting cache miss.

This sequence moves the stale interval from the configured TTL to event-publication and queue-consumption time. Reads continue using the existing cache path while the queue carries invalidation work.

## Four-week results

We counted a stale read when a request received a cache entry superseded by a catalog change. Over four weeks, stale reads fell from 3.1% to 0.04% of requests.

That change represents a 3.06 percentage-point decrease and a 98.7% relative reduction from the TTL-based rate. The remaining 0.04% shows that event-driven invalidation reduced stale reads without eliminating them.

Request p99 latency remained 41 ms before and after the switch. The invalidation queue peaked at 1,200 events per second during a sale day.

The p99 measurement shows that the new path did not change latency at that percentile. The sale-day peak provides a measured capacity baseline for the publisher, queue, and consumer.

## The operational tradeoff

TTL expiry bounded a stale entry’s lifetime by the configured TTL. Event-driven invalidation makes freshness depend on successful event publication and consumption.

If event delivery fails, an affected entry can remain stale because elapsed time no longer triggers its removal. We monitor publication failures, consumer failures, and queue lag as three cache-correctness signals.

The queue is not part of the synchronous request path, but it is part of the catalog’s correctness path. Capacity planning must cover at least the measured peak of 1,200 invalidation events per second.

## Guidance for similar migrations

Before replacing TTL expiry, establish measurements for stale-read rate, request latency, queue throughput, and queue lag.

1. Define a stale read using a catalog version or another authoritative change marker.
2. Emit invalidation events only after the corresponding catalog change commits.
3. Make repeated invalidations safe because queue delivery can produce duplicate events.
4. Track queue lag because delayed consumption extends the stale interval.
5. Test throughput against the highest measured update rate.
6. Compare p99 request latency before and after enabling event-driven invalidation.

For our catalog, entry age was an inadequate proxy for validity. Event-driven invalidation reduced stale reads from 3.1% to 0.04% while p99 latency remained 41 ms.
