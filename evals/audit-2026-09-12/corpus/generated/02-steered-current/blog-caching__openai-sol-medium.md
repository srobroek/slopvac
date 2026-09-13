# Why We Replaced TTL Expiry with Event-Driven Catalog Cache Invalidation

Our product catalog cache used TTL-based expiry to remove entries after a fixed interval. We replaced that policy with invalidation events tied to catalog changes.

During a four-week measurement period, stale reads fell from 3.1% to 0.04% of catalog requests. The p99 request latency remained 41 ms. The invalidation queue peaked at 1,200 events per second during a sale day.

## The problem with TTL expiry

TTL expiry bounds how long a cache entry can remain stale. It does not remove the entry when the underlying product changes.

A longer TTL increases the interval during which requests can receive obsolete prices, availability, or product details. A shorter TTL reduces that interval but increases cache misses and catalog reads.

Our stale-read rate reached 3.1% under the TTL policy. That rate made expiry timing part of the product update path, even though the cache received no direct signal when data changed.

## The event-driven model

The new model connects cache validity to catalog changes rather than elapsed time. Each catalog change creates an invalidation event for the affected cache entry.

The processing path has four steps:

1. Commit the catalog change.
2. Publish an invalidation event that identifies the changed catalog data.
3. Consume the event from the invalidation queue.
4. Remove the corresponding entry from the cache.

The next request repopulates the removed entry from the catalog data source. This sequence limits stale reads to the interval between the catalog commit and invalidation processing.

## Why we switched

TTL expiry and catalog updates use separate clocks. An entry can therefore remain valid in the cache after its catalog record changes.

Event-driven invalidation ties cache removal to the event that makes the cached value obsolete. This relationship addresses stale reads without requiring a shorter TTL for every entry.

The four-week measurement showed a 3.06 percentage-point reduction in stale reads. The relative reduction was 98.7%, and requests were 77.5 times less likely to return stale catalog data.

## Latency impact

The p99 request latency measured 41 ms before and after the switch. The observed stale-read reduction therefore did not coincide with a p99 latency increase during the four-week period.

Invalidation work runs through a queue rather than in the catalog request path. The queue reached 1,200 events per second at its sale-day peak.

The observed peak is a traffic measurement, not a queue capacity limit. Capacity planning must account for a higher event rate and the acceptable invalidation delay during a backlog.

## Operational requirements

Event-driven invalidation replaces TTL timing with a delivery pipeline. That pipeline must preserve cache correctness during duplicate events, delayed events, and consumer restarts.

Our operating checks cover these signals:

- Measure the delay between each catalog commit and its completed cache invalidation.
- Track the invalidation queue depth and event age.
- Retry invalidations that fail before cache removal.
- Make repeated invalidations safe for the same cache key.
- Compare cached values with catalog values to measure stale reads.
- Alert when the event rate approaches the tested queue throughput.

TTL expiry can remain as a fallback bound for entries that miss an invalidation event. The event remains the primary invalidation mechanism, while the TTL limits the lifetime of an orphaned entry.

## What the measurements show

Over four weeks, event-driven invalidation reduced stale reads from 3.1% to 0.04% of requests. The p99 request latency remained at 41 ms across the comparison.

The sale-day peak established an observed queue load of 1,200 events per second. It did not establish behavior above that rate or during a prolonged consumer outage.

These measurements support event-driven invalidation for our product catalog workload. Teams evaluating the same design should measure stale-read rate, invalidation delay, request latency, and queue behavior against their own traffic.
