# Why We Replaced TTL Expiration with Event-Driven Cache Invalidation

Our product catalog cache once removed entries after a fixed TTL. We replaced that policy with invalidation events triggered by catalog changes.

Over four weeks, stale reads fell from 3.1% to 0.04% of requests. The p99 request latency remained 41 ms.

## The TTL consistency window

TTL expiration limited each stale entry’s lifetime, but it did not prevent stale reads during that interval. A product update and its cached representation could differ until the TTL elapsed.

Reducing the TTL would have shortened this interval. It also would have increased cache misses and placed more read traffic on the catalog data store.

Increasing the TTL would have improved cache retention. It also would have extended the interval when requests could receive outdated product data.

This tradeoff made expiration time a proxy for data consistency. Our catalog required invalidation to follow changes instead of elapsed time.

## The event-driven model

The catalog now emits an invalidation event when product data changes. The invalidation consumer uses each event to remove the corresponding cache entry.

The next request reads the updated product data and repopulates the cache. Unchanged products retain their cached entries without periodic expiration.

This model ties cache freshness to catalog changes. The TTL no longer determines how long an updated product can remain stale.

## Four-week results

We compared request measurements across a four-week observation period.

| Metric | TTL expiration | Event-driven invalidation |
|---|---:|---:|
| Stale reads | 3.1% | 0.04% |
| p99 latency | 41 ms | 41 ms |

Event-driven invalidation reduced stale reads by 3.06 percentage points. That change represents a 98.7% reduction from the 3.1% baseline.

The p99 latency remained unchanged at 41 ms. The consistency improvement therefore did not change the measured tail latency.

## Sale-day queue traffic

The invalidation queue peaked at 1,200 events per second during a sale day. This peak measured the highest observed invalidation rate during the four-week period.

That measurement does not establish the queue’s maximum capacity. It establishes that the event-driven path handled the observed sale-day rate while p99 latency remained 41 ms.

## What changed in our design

TTL expiration asked the cache to infer freshness from age. Event-driven invalidation lets the catalog identify entries that became outdated.

The distinction matters when updates arrive at irregular rates. A fixed TTL applies the same expiration policy to frequently changed products and unchanged products.

Event-driven invalidation concentrates work on actual catalog changes. It also makes the invalidation queue part of the catalog’s consistency path.

Teams adopting this model must measure stale-read rate, invalidation throughput, and request latency together. Queue throughput alone does not show whether consumers invalidate entries before requests read stale data.

## Outcome

We switched because TTL expiration could only bound stale-read duration. It could not align cache invalidation with catalog updates.

Across four weeks, event-driven invalidation reduced stale reads from 3.1% to 0.04%. The p99 latency remained 41 ms, including a sale day when the queue peaked at 1,200 events per second.
