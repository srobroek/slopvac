# Why We Replaced TTL Expiry with Event-Driven Cache Invalidation

Our product catalog cache used time-to-live (TTL) expiry until stale reads became a measurable correctness problem. We replaced TTL expiry with event-driven invalidation and measured the result for four weeks.

Stale reads fell from **3.1% of requests to 0.04%**. P99 latency remained **41 ms**. On a sale day, the invalidation queue reached **1,200 events per second**.

## TTL expiry created a predictable stale-read window

TTL expiry removes an entry after a configured duration. The cache does not know that the underlying catalog changed before that duration ends.

For example, a price update could reach the catalog database while the cache still served the previous price. The cache would continue serving that value until its TTL expired or another request refreshed the entry.

Shorter TTL values reduce the maximum stale period. They also increase cache misses and refresh traffic.

Longer TTL values improve cache reuse. They also extend the period during which the cache can serve an outdated product record.

Our previous configuration required us to choose between these effects. Product updates could arrive at any time, so one fixed TTL could not match every update pattern.

## Catalog changes now emit invalidation events

The catalog service emits an invalidation event when it changes a product record. The cache consumer reads that event and removes the affected cache entry.

The next request loads the updated record from the catalog service. The cache then stores that record for later requests.

This flow ties cache removal to the catalog change instead of to an elapsed time interval.

The event identifies the product record that changed. The consumer invalidates that record rather than clearing the complete product catalog cache.

## The four-week measurement showed a correctness improvement

We compared the previous TTL-based cache with the event-driven cache over four weeks.

| Metric | TTL expiry | Event-driven invalidation |
|---|---:|---:|
| Stale reads | 3.1% of requests | 0.04% of requests |
| P99 latency | 41 ms | 41 ms |
| Invalidation throughput | Not applicable | 1,200 events/second peak |

The stale-read rate decreased by **3.06 percentage points**. Relative to the previous rate, that represents a **98.7% reduction**.

P99 latency did not change in the measured comparison. Both configurations recorded **41 ms** at the 99th percentile.

The latency result matters because invalidation improved freshness without adding a measured tail-latency cost. The cache still handles normal reads through the same lookup path after an invalidation removes an entry.

## Queue capacity became an explicit operating concern

TTL expiry distributed refresh work across requests and expiration times. Event-driven invalidation moves catalog-change work into an invalidation queue.

That queue reached **1,200 events per second** during one sale day. The peak gave us a concrete throughput requirement for the consumer and its monitoring.

The queue now represents pending freshness work. Queue growth indicates that invalidation consumers are processing events more slowly than catalog updates produce them.

A queue backlog can delay invalidation even when the catalog service has already committed a change. We therefore monitor queue throughput and peak depth as part of cache operations.

## Event delivery defines the correctness boundary

Event-driven invalidation depends on the catalog change producing an event and the consumer processing it.

A missing event leaves the corresponding cache entry untouched. A delayed event extends the stale period until the consumer processes it.

The cache consumer must therefore handle duplicate events safely. Reprocessing the same product invalidation must leave the cache in the same state as processing it once.

The system also needs a recovery path for events that fail processing. That path must allow operators to identify and replay affected invalidations.

These requirements do not make event-driven invalidation maintenance-free. They make freshness behavior observable through event throughput and queue state.

## What changed for our design

We changed the cache contract from “refresh after a fixed duration” to “invalidate after a catalog change event.”

That contract reduced stale reads from **3.1% to 0.04%** during the four-week measurement period. It preserved the measured P99 latency of **41 ms**.

The sale-day peak of **1,200 events per second** established the queue throughput that our production design must accommodate.

For catalog data where correctness depends on recent updates, event-driven invalidation gave us a lower measured stale-read rate without changing measured P99 latency.
