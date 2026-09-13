# Why We Replaced TTL Expiry with Event-Driven Cache Invalidation

Our product catalog cache used time-to-live expiry to remove cached entries. We replaced that policy with invalidation events tied to catalog updates.

During a four-week measurement period, stale reads fell from 3.1% to 0.04% of requests. The change reduced the stale-read rate by 98.7% relative to the TTL-based baseline.

Request p99 latency remained 41 ms under both policies. On a sale day, the invalidation queue peaked at 1,200 events per second.

## The limitation of TTL expiry

A TTL policy accepts stale data between a catalog update and the cached entry’s expiration. Shorter TTL values narrow that interval but increase cache misses and catalog reads.

Catalog changes do not follow a fixed schedule. Price updates, inventory changes, and sale events can occur before any configured TTL expires.

This mismatch made expiration time a proxy for data validity. The cache could retain an outdated entry even though the product catalog had already changed.

## The event-driven model

The new model connects cache validity to catalog updates. A catalog change publishes an invalidation event for the affected cached data.

The invalidation consumer processes that event and removes the corresponding entry. The next request reloads the product data through the cache’s existing miss path.

TTL expiry remains unsuitable as the primary validity signal because elapsed time does not identify a catalog change. An invalidation event identifies that change directly.

## Queue capacity mattered

Event-driven invalidation moved part of the cache’s workload onto the invalidation queue. That queue peaked at 1,200 events per second during a sale day.

Sale traffic provided the highest observed invalidation rate in the four-week measurement period. We used that peak to evaluate queue throughput rather than relying on average traffic.

A queue backlog extends the interval during which cached entries can remain stale. Queue depth and event-processing delay therefore became cache-correctness signals.

## Measured results

| Metric | TTL expiry | Event-driven invalidation |
|---|---:|---:|
| Stale reads | 3.1% of requests | 0.04% of requests |
| Request p99 latency | 41 ms | 41 ms |
| Peak invalidation rate | Not applicable | 1,200 events per second |

The stale-read rate dropped by 3.06 percentage points over four weeks. Request p99 latency stayed at 41 ms, so the measured correctness gain did not change tail latency.

## Why we switched

TTL expiry based cache validity on a timer. Event-driven invalidation bases cache validity on the catalog update that changes the data.

The four-week results supported the switch. Stale reads fell from 3.1% to 0.04%, while request p99 latency remained 41 ms.

The new design also exposed invalidation throughput as an operating constraint. The sale-day peak of 1,200 events per second provides a measured capacity baseline for the queue and its consumers.
