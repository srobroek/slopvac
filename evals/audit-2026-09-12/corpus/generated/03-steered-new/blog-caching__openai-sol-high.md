# Why We Replaced TTL Expiry with Event-Driven Cache Invalidation

Our product catalog cache previously expired entries after a fixed time-to-live period. We replaced that policy with invalidation events triggered by catalog changes.

The change reduced stale reads from 3.1% to 0.04% across a four-week measurement window. The p99 request latency remained 41 milliseconds.

## TTL measured age instead of validity

A TTL determines how long the cache retains an entry. It cannot determine whether the underlying catalog record changed during that period.

A catalog update could make a cached entry stale immediately after the cache stored it. Requests then received that stale value until the TTL expired.

A shorter TTL would reduce the maximum stale period. It would also increase cache refills from the catalog data store.

A longer TTL would reduce refill frequency. It would also extend the period when requests could receive stale values.

Our freshness requirement depended on catalog changes, not elapsed time. Event-driven invalidation aligned cache removal with those changes.

## The event-driven flow

Each catalog change publishes an invalidation event to a queue. An invalidation consumer removes the cache entry identified by that event.

The next request reads the updated record from the catalog data store. That request then repopulates the cache.

The request path does not wait for the invalidation queue. Requests continue to read the cache before accessing the catalog data store.

This design moves the freshness boundary from TTL duration to event-processing delay. Queue lag therefore becomes a direct indicator of stale-read risk.

## Four-week results

We compared the TTL policy with event-driven invalidation over four weeks.

| Metric | TTL expiry | Event-driven invalidation |
|---|---:|---:|
| Stale reads | 3.1% of requests | 0.04% of requests |
| p99 request latency | 41 ms | 41 ms |
| Peak invalidation rate on a sale day | Not applicable | 1,200 events per second |

Stale reads decreased by 3.06 percentage points. The relative reduction was 98.7% against the 3.1% TTL baseline.

The p99 latency remained 41 milliseconds under both policies. Moving invalidation outside the request path preserved the measured tail latency.

## Sale-day traffic tested the queue

A sale day produced the highest observed invalidation rate. The queue peaked at 1,200 events per second.

That peak matters because catalog writes can arrive in bursts. Invalidation consumers must process those bursts before queue lag creates a stale-read window.

Capacity planning now uses event throughput alongside request throughput. The two workloads measure different pressure on the catalog cache.

## The trade-off changed

TTL expiry concentrates operational risk in one duration setting. That setting balances stale-read duration against cache-refill frequency.

Event-driven invalidation replaces that duration trade-off with an event-delivery requirement. The system must publish, retain, and process each invalidation event.

That requirement gives us a measurable control point. We can track queue throughput and compare it with the 1,200-events-per-second observed peak.

For our product catalog, the four-week results support the change. Stale reads fell to 0.04% without moving p99 latency above 41 milliseconds.
