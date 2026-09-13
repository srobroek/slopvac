# Why We Replaced TTL Expiry with Event-Driven Cache Invalidation

Our product catalog cache used time-to-live (TTL) expiry to decide when cached data became invalid. After measuring stale reads at 3.1% of requests, we replaced TTL expiry with event-driven invalidation.

Over the following four weeks, stale reads fell to 0.04% of requests. The reduction was measured against the previous 3.1% rate. p99 latency remained 41 ms, and the invalidation queue peaked at 1,200 events per second during a sale day.

## TTL expiry delayed catalog changes

A TTL cache serves an entry until its expiration time. The cache does not know that a catalog record changed before that expiration time.

For a product price or availability update, the cache could therefore return the previous value during the remaining TTL interval. Shortening the TTL would reduce that interval, but it would also cause more entries to expire before they required replacement.

The 3.1% stale-read rate showed that the expiration interval did not match the catalog’s update behavior.

## Events identify the invalid entries

Event-driven invalidation connects catalog changes to cache removal.

When a catalog record changes, the system emits an invalidation event for that record. The cache consumer processes the event and removes the affected entry. The next request loads the changed record instead of serving the previous cached value.

This approach invalidates an entry because a known change occurred. TTL expiry invalidates an entry because a timer elapsed.

## The measured result

We compared the previous TTL-based behavior with the event-driven implementation over four weeks.

| Metric | TTL expiry | Event-driven invalidation |
|---|---:|---:|
| Stale reads | 3.1% of requests | 0.04% of requests |
| p99 latency | 41 ms | 41 ms |
| Peak invalidation rate | Not applicable | 1,200 events/second |

The stale-read rate decreased by 3.06 percentage points, from 3.1% to 0.04%. That represents approximately 98.7% fewer stale reads relative to the TTL-based rate.

p99 latency did not change in the measured comparison. Both implementations recorded 41 ms.

## Queue capacity became an explicit operating metric

Event-driven invalidation adds a queue that TTL expiry does not require. The queue carries invalidation events from catalog changes to cache consumers.

The queue reached 1,200 events per second during a sale day. We use that peak as the observed event-ingestion rate for operational capacity checks.

Queue behavior also gives us a direct signal for delayed invalidation. A growing backlog means cache removal is not keeping pace with catalog changes. TTL expiry provides no equivalent backlog measurement because expiration happens independently for each cached entry.

## What changed for the cache

The cache now treats catalog change events as invalidation inputs. TTL no longer determines when a changed catalog entry becomes invalid.

The cache still needs a response when an invalidation event is delayed or lost. We retain a fallback expiration policy for that failure condition, but event processing handles normal catalog changes.

This design makes the event path the primary freshness mechanism and the expiration path the recovery mechanism.

## What we learned

The main improvement came from matching invalidation to the event that made cached data obsolete. The measured stale-read rate fell from 3.1% to 0.04% without changing p99 latency from 41 ms.

The trade-off is operational visibility. Event-driven invalidation requires monitoring event throughput and queue backlog. Our sale-day peak of 1,200 events per second defines the load that the invalidation path must handle.

For data that changes at identifiable events, invalidation can provide fresher reads than a fixed TTL while preserving the measured latency profile. Teams considering the same change should measure stale reads, p99 latency, event rate, and queue backlog before and after the migration.
