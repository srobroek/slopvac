# Why We Replaced TTL Expiry with Event-Driven Cache Invalidation

Our product catalog cache served stale data for 3.1% of requests under TTL-based expiry. We replaced fixed expiration with event-driven invalidation to remove affected entries when catalog data changed.

After four weeks, stale reads fell to 0.04% of requests. The change reduced stale reads by 3.06 percentage points, or 98.7% relative to the previous rate.

## The problem with TTL-based expiry

TTL-based caching assigns each entry an expiration time. The cache continues serving an entry until that time passes, even when the underlying catalog record changes.

A shorter TTL reduces the stale-data window. A shorter TTL also increases cache misses and origin reads.

A longer TTL improves cache retention. A longer TTL increases the time that customers can receive outdated prices, availability, or product details.

The TTL forced us to choose between freshness and cache efficiency. The product catalog needed freshness when updates occurred, rather than after an unrelated timer expired.

## The event-driven model

The catalog now emits an invalidation event when a product changes. The cache consumes that event and removes the affected entry.

The next request loads the updated product data and repopulates the cache. Unchanged products remain cached until another product event targets them.

This model ties invalidation to the catalog change itself. A product update no longer waits for the entry's remaining TTL.

The invalidation event identifies the product affected by the change. The cache uses that product identity to remove the corresponding entry.

## What we measured

We compared the TTL-based cache with the event-driven cache across four weeks. We measured stale reads as a percentage of product catalog requests.

| Metric | TTL-based expiry | Event-driven invalidation |
| --- | ---: | ---: |
| Stale reads | 3.1% of requests | 0.04% of requests |
| p99 latency | 41 ms | 41 ms |

The stale-read rate decreased from 3.1% to 0.04%. The p99 latency remained 41 ms before and after the change.

The results show that the invalidation path improved freshness without changing the measured p99 latency. The cache still handled requests within the same p99 latency boundary.

## Queue behavior during a sale

The invalidation queue peaked at 1,200 events per second on a sale day. That peak represented the highest observed invalidation rate during the four-week measurement period.

The queue allowed catalog updates to reach the cache through an asynchronous path. The cache processed invalidations without adding the event publication work to the product request path.

A queue peak does not prove that every invalidation completed immediately. We therefore treat queue depth and event age as operational signals alongside stale-read measurements.

## What changed for operations

TTL monitoring focused on expiration rates, cache misses, and origin traffic. Event-driven invalidation added queue throughput, queue depth, and consumer processing as operational signals.

The invalidation queue became part of the catalog cache's correctness path. A delayed or failed consumer can leave an outdated entry in the cache.

Stale-read measurement remains the primary freshness check. Queue metrics help identify the cause when stale reads increase.

## When event-driven invalidation fits

Event-driven invalidation fits catalogs that already publish reliable product-change events. It also fits systems where stale data causes a measurable customer or business impact.

TTL expiry remains useful when data changes rarely, freshness requirements allow bounded staleness, or no change event exists. A TTL can also provide a fallback expiration boundary for entries that miss their invalidation event.

Our catalog required updates to become visible without waiting for a fixed expiration interval. Event-driven invalidation reduced stale reads from 3.1% to 0.04% while keeping p99 latency at 41 ms.
