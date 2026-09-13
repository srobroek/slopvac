# Why We Ditched TTL-Based Cache Expiry for Event-Driven Invalidation

**Posted by the Platform Engineering Team**

Every engineer knows the pain: your cache is serving stale data, users are seeing yesterday's prices, and your TTL is either too short (thrashing the backend) or too long (business logic breaking). Over the past four weeks, we replaced our TTL-based product catalog cache with event-driven invalidation—and the results validated what we suspected all along: waiting for a timer to expire is lazy engineering.

## The Old World: TTL-Based Expiry

For years, our product catalog lived in a distributed cache (Redis) with a simple 30-second TTL. When a product updated—price change, inventory adjustment, description fix—the database updated, but the cache entry remained valid for another half minute. This seemed reasonable at first. Thirty seconds of stale reads weren't catastrophic, and it kept our database query load manageable.

Then sales started.

During flash sales and inventory corrections, 30 seconds felt like an eternity. Customers would see an old price, add to cart, and see a different amount at checkout. Our monitoring showed stale reads spiking to **3.1% of all requests** on high-traffic days. Support tickets piled up. Product management got frustrated. We implemented shorter TTLs in select scenarios, which helped but created operational complexity—different TTLs for different product types, special handling during sales, manual cache invalidation endpoints we'd never publicly admit to using.

The fundamental problem was philosophical: we were defending against staleness with time, not truth. A TTL doesn't know whether data has changed; it just knows whether enough seconds have elapsed. In 29 seconds, the catalog could shift completely, and we'd still be serving the old version.

## The Trigger: A Better Idea

Event-driven invalidation flips the model. Instead of passively waiting for TTL expiry, we actively invalidate the cache when the source data changes. When a product price updates in the database, an event fires. That event triggers cache invalidation. The next request gets fresh data.

This isn't revolutionary—it's been the right pattern for years. We finally had a few things in place to implement it:

1. **Event bus** – We'd already invested in Kafka for order events. Adding product catalog events was straightforward.
2. **Cache coordination** – Implementing proper event handlers in our cache clients (using Redis pub/sub as a fallback).
3. **Operational readiness** – Our on-call team had capacity to support a new component.

## Implementation: The Details

Our product service publishes an event to Kafka whenever the catalog changes:

```json
{
  "type": "product.updated",
  "productId": "sku-12345",
  "timestamp": "2026-09-12T14:32:15Z",
  "changes": ["price", "inventory"]
}
```

Cache clients subscribe to these events. On receipt, they delete the relevant cache entry—nothing fancy. The next request rebuilds it from the database, guaranteeing freshness.

We added a wrinkle: **event batching at high throughput**. During peak sales, events arrive fast enough that invalidating one at a time would thrash the message queue. Instead, our service buffers invalidation events for 50 milliseconds, deduplicates by product ID, and invalidates in bulk. This reduced queue pressure without introducing unacceptable staleness windows.

We also kept TTL as a safety net. Cache entries expire after 5 minutes now (up from 30 seconds), but this is a fallback, not the primary mechanism. If the event pipeline hiccups, the TTL catches it.

## The Results

After four weeks in production, the data was unambiguous:

- **Stale reads**: 3.1% → 0.04% (97% reduction)
- **P99 latency**: 41 ms → 41 ms (no regression)
- **Max queue throughput**: 1,200 events/second on sale days
- **Event processing latency**: P99 < 100 ms
- **Cache invalidation accuracy**: 99.97%

Stale reads didn't hit zero because of eventual consistency windows in our data pipeline and a small percentage of malformed events that we handle gracefully. But 0.04% is the noise floor—customer-visible staleness became exceptionally rare.

The latency result mattered most to us. We were nervous about the operational overhead of event processing, but 41 ms p99 stayed flat because cache hits still dominate (99%+ of traffic hits hot data), and invalidation is cheap—a delete operation on Redis is microseconds.

## What Surprised Us

**Event ordering**: At scale, Kafka partitioning means events can arrive out of order. We had a subtle bug where a newer event arrived before an older one, causing us to invalidate fresh data. We fixed it by versioning cache entries with sequence numbers.

**Monitoring complexity**: Counting stale reads accurately requires careful instrumentation. We tag cache entries with write timestamps, compare them to database versions periodically, and alert on divergence. This adds overhead, but it's critical for visibility.

**Event storm during deployments**: Rolling updates of the product service caused event bursts as the same products were updated by multiple instances. We implemented deduplication windows and idempotency keys to handle this.

## Trade-offs: Nothing Is Free

Event-driven invalidation isn't universally superior. The trade-offs we accepted:

- **Complexity**: More moving parts. Kafka, event handlers, versioning logic. More to break.
- **Debugging**: Stale data in production is harder to diagnose when it depends on event timing.
- **Operational cost**: Running event infrastructure costs money. Our Kafka cluster isn't free.

For a small system with low update frequency, TTL-based caching is simpler and probably sufficient. For a catalog with thousands of updates per second, event-driven invalidation pays for itself in reduced staleness and better customer experience.

## Lessons for Your System

If you're running similar patterns:

1. **Measure before optimizing**: We had numbers on stale reads before we started. Don't guess.
2. **Keep a fallback**: TTL as a safety net—not the primary strategy, but there if things break.
3. **Batch at scale**: Individual event processing hits limits. Coalesce when throughput spikes.
4. **Version your data**: Sequence numbers saved us from ordering bugs. The overhead is worth it.
5. **Instrument heavily**: You can't tune what you can't see. Cache hit rates, staleness metrics, event latency—log it all.

## What's Next

We're exploring two extensions:

- **Partial invalidation**: Instead of deleting entire cache entries, invalidate specific fields. Useful when price changes but description doesn't.
- **Predictive TTL**: Machine learning on access patterns to set adaptive TTLs for entries that rarely change.

But honestly, for now, the system is stable and doing exactly what we need. Sometimes the right engineering is the boring engineering.

---

**Questions?** Find us at [slack channel] or leave a comment. We're always happy to discuss cache strategies and tradeoffs over coffee.
