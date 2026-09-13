# Replacing TTL Caches with Event-Driven Invalidation: What We Learned

For three years, our product catalog cache used a 30-second time-to-live (TTL) across 15 million SKUs. Every half-minute, stale data persisted: customers added items to carts that were already discontinued, prices displayed were off by one cycle, and inventory showed stock we had already sold. At peak load (sale days), 3.1% of catalog requests served stale reads. That number drove us to rebuild the cache layer.

## The Problem

Our platform serves 400,000 requests per second at peak. A TTL-based cache is simple: set an expiry time, flush everything when it expires, refill on the next read. The tradeoff is baked in—you choose staleness or miss rate. We chose a short TTL to minimize staleness, but that pushed more requests through the database on cache misses, and the 3.1% of stale reads still violated our SLA.

When a sale starts, 50,000 SKUs change prices in under 10 seconds. TTL meant some customers saw old pricing for up to 30 seconds after the change. When inventory updates spike, the same delay compounds: a fulfillment center ships 200 units, our system receives the stock event, but a customer's browser still loads old stock data because the cache is still good for another 28 seconds.

## The Solution

We built an event-driven invalidation layer. Whenever a catalog change occurs—price update, inventory correction, product metadata change—the catalog service publishes an event to Kafka. A lightweight invalidator subscribes to these events, plucks the SKU ID, and sends a direct cache invalidation to all six regional cache nodes. The entry vanishes instantly. The next request fills it with fresh data from the database.

The change required four weeks of work:

- We instrumented the catalog service to publish structured events for every mutation (price, inventory, metadata, descriptions).
- We built an invalidator service to consume Kafka events and fan out cache-delete commands to each region.
- We added circuit breakers: if Kafka is down or the invalidator crashes, the cache falls back to a shorter TTL of 5 seconds (vs. 30 previously).
- We added metrics on event lag, invalidation success, and cache hit rate per SKU.

## Measured Results

Over four weeks of production traffic (July 15 through August 11), we ran both systems in parallel and compared outcomes:

**Stale reads**: 3.1% → 0.04%.
This is a 98-fold improvement. We measured stale reads by querying the database for the ground truth and comparing it to what the cache served 5 seconds later, sampled at 1 in 10,000 requests.

**p99 request latency**: 41 ms → 41 ms.
The cache invalidation overhead added zero measurable latency to the catalog endpoint. Invalidation commands are asynchronous; we do not wait for them before returning a response.

**Invalidation queue**: peaked at 1,200 events per second during the July 28 sale.
We dimensioned the Kafka topic at 10 partitions and the invalidator fleet at 12 instances. Both stayed under 40% utilization. No event was ever dropped, and end-to-end latency from mutation to cache invalidation was under 150 ms at the 99th percentile.

**Database load**: flat at 8,000 requests per second.
The shorter TTL fallback and higher cache accuracy meant the database saw no change in request volume. We feared the switch would push more traffic downstream; it did not.

## What We Learned

Event-driven invalidation is not cheaper than TTL caching—we added infrastructure (Kafka, the invalidator service, circuit breaker logic). But the cost trades for specificity: we no longer invalidate everything on a timer. We invalidate only what changed, the instant it changed. For a catalog of millions, this pays.

Kafka was the right choice for us because we already had it for order events and inventory sync. If you do not have a message broker, you might use a simple HTTP fanout or a pub/sub system. The shape of the pattern (publish event → invalidate directly) is portable; the transport is not.

We kept the fallback TTL at 5 seconds. It is a safety net: if the invalidation path breaks, the cache still prevents the database from melting, and staleness degrades gracefully. We have never hit this fallback in production—the invalidator has 99.96% availability across the period—but it exists because TTL is predictable and event-driven systems fail in unexpected ways.

The 0.04% stale read rate is near zero but not zero. It comes from time-skew between regions: an invalidation command reaches one cache node and not another for a few milliseconds. We could eliminate this with distributed consensus or by reading from the primary region first, but the cost outweighs the benefit. 0.04% is acceptable.

## For Your Team

If your cache hit rate is high and staleness is low, TTL is probably fine. If you serve millions of mutable items and changes matter within seconds, event-driven invalidation is worth the engineering cost. Start with fallback TTL so you can ship the system in phases and roll back without fear. Measure both staleness and latency before you claim a win; we did not expect latency to stay flat, and it did.
