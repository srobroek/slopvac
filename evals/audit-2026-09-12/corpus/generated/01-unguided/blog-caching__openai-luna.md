# Why We Replaced TTL Expiry with Event-Driven Cache Invalidation

For years, our product catalog cache used a familiar strategy: write an item to the cache with a time-to-live, then wait for the entry to expire.

It was simple, operationally predictable, and mostly effective. It was also the source of a class of correctness problems we could no longer ignore. Product updates were not reflected until the TTL elapsed, which meant that customers could see outdated prices, availability, or descriptions even though the source of truth was already correct.

We recently replaced TTL-based expiry with event-driven invalidation. Over a four-week measurement period:

- Stale reads fell from **3.1% of requests to 0.04%**.
- **p99 latency remained unchanged at 41 ms**.
- The invalidation queue reached a peak of **1,200 events per second** during a sale day.

The change did not make caching free of complexity. It moved complexity from guessing an acceptable expiration window to reliably propagating changes. For our catalog, that was the better trade.

## The problem with waiting for a clock

Our original cache flow looked roughly like this:

1. A request checked the cache.
2. On a miss, the service read the product from the catalog database.
3. The service stored the result with a TTL.
4. Updates changed the database, but did not immediately change the cache.
5. Consumers saw the new value only after the corresponding cache entry expired.

The TTL was a compromise between freshness and load:

- A short TTL reduced the stale-read window but increased database traffic and cache churn.
- A long TTL improved hit rate and reduced backend load but allowed stale values to persist longer.

There was no TTL that worked well for every catalog field or every operational event. A product description could tolerate minutes of staleness. A price or inventory flag often could not. Sales and bulk catalog updates made the problem more visible because many entries changed at once.

The issue was not that the cache was malfunctioning. It was doing exactly what we had configured it to do. The problem was that time-based expiration encoded an indirect assumption:

> If a value has not changed for this amount of time, it is probably safe to keep serving it.

That assumption was weakest precisely when updates mattered most.

## Why event-driven invalidation fit the catalog

The catalog system already knew when products changed. Product updates passed through our write path and generated domain events. Those events included the product identifier and the type of change, such as:

- Product metadata updated
- Price changed
- Availability changed
- Product unpublished
- Product deleted

Instead of waiting for the cached value to expire, we now use those events to remove or refresh the affected cache entries.

The resulting flow is:

1. A product update is committed to the source of truth.
2. The update produces a catalog-change event.
3. An invalidation consumer receives the event.
4. The consumer deletes the corresponding cache entry.
5. The next request loads the current value and repopulates the cache.

In simplified form:

```text
catalog write
    |
    +--> source of truth
    |
    +--> product-changed event
             |
             +--> invalidation queue
                      |
                      +--> cache invalidator
                               |
                               +--> delete product key
```

We retained a long TTL as a safety net. The TTL is no longer our primary freshness mechanism; it limits how long an entry can survive if an invalidation event is delayed, lost, or malformed.

That distinction matters. Event-driven invalidation gives us prompt invalidation under normal operation, while the TTL provides eventual cleanup and protection against certain classes of failure.

## The consistency boundary

A cache invalidation event must not be published before the underlying write is durable. Otherwise, a consumer could remove a cache entry for a database update that later rolls back or never becomes visible.

We therefore treat the update and event publication as one consistency problem. Our implementation uses a durable change record associated with the catalog write. A separate publisher delivers that record to the invalidation queue after the write is committed.

This gives us the delivery properties we need:

- Events survive a temporary queue or consumer outage.
- Consumers can retry failures.
- A product update is not considered fully propagated until its event is acknowledged.
- Replaying an event is safe.

The invalidator is intentionally idempotent. Deleting a key that is already absent is harmless, and processing the same product-change event more than once produces the same result.

## Why we invalidate instead of updating the cache in place

At first, updating cached objects directly seemed more efficient than deleting them. In practice, invalidation was a safer first step.

An event may contain only a partial view of the change. It may identify the product and the changed fields without containing the complete object required by every cache representation. Our catalog also has multiple cache keys and derived views, including localized and summarized representations.

Deleting the relevant keys avoids duplicating catalog transformation logic in the event consumer. The next cache fill goes through the same read path used for a normal miss and constructs the representation from the current source of truth.

This does introduce a small cache-miss spike after a large update. We accepted that cost because it makes the invalidation path simpler and reduces the chance of writing an incomplete or incorrectly transformed object into the cache.

For particularly hot products, we can later add asynchronous refresh or request coalescing. We did not make those optimizations prerequisites for the migration.

## Handling duplicates, ordering, and races

Distributed event systems rarely provide exactly-once processing in the way application developers initially imagine. We designed for at-least-once delivery and out-of-order events.

### Duplicate events

The invalidation operation is idempotent, so duplicate events are safe. We also attach event identifiers and processing metadata for observability and troubleshooting, but correctness does not depend on deduplicating every message.

### Out-of-order events

Because the operation is deletion rather than mutation, event ordering is less important. A newer event followed by an older event still results in the key being absent. The next read obtains the current value.

If we had used events to write complete objects into the cache, ordering would have been much more consequential. Avoiding that coupling was one of the reasons we chose delete-and-refill semantics.

### Writes racing with reads

There is still a race between a cache fill and an invalidation:

1. A read misses the cache and begins loading a product.
2. The product is updated.
3. The invalidation removes the old cache entry.
4. The read finishes using a value loaded before the update and writes it to the cache.

This is the most important correctness edge case in the design. We addressed it by associating catalog versions with reads and cache fills. A fill is written only if its source version is still current. If the version has advanced, the fill is discarded and the next read reloads the product.

The exact mechanism is implementation-specific, but the principle is general: invalidation alone is not sufficient if a concurrent read can repopulate the cache with an older value.

## The operational trade-off

TTL-based caching gave us a relatively quiet operational model. Event-driven invalidation introduced a new subsystem with its own failure modes:

- Queue backlog
- Consumer lag
- Poison messages
- Event schema changes
- Retry storms
- Misrouted or missing invalidations
- Cache-key mapping bugs

We made these conditions visible before switching traffic over. The invalidation pipeline now exposes:

- Queue depth and age of the oldest event
- Events processed per second
- Consumer error and retry rates
- Invalidations by product and event type
- Time from committed update to cache deletion
- Cache fills that were rejected because their source version was stale
- Dead-letter volume

We alert primarily on event age and propagation delay rather than queue depth alone. A queue can contain many events and still be healthy if consumers are processing them quickly. Conversely, a small queue with a stalled consumer can represent a serious freshness problem.

## What happened on the sale day

The highest load during the measurement period occurred on a sale day, when bulk price and availability updates generated a peak of **1,200 invalidation events per second**.

The queue absorbed the burst, and consumers caught up without affecting request p99 latency. This was an important test because a sale combines the conditions that are most problematic for TTL caching:

- A large number of related products change together.
- Those changes happen close to a high-traffic period.
- Fresh prices and availability are particularly important.
- Cache misses can increase immediately after invalidation.

We monitored both the invalidation pipeline and the catalog read path during the event. The invalidation queue peaked at 1,200 events per second, while request **p99 latency remained 41 ms**, unchanged from the pre-migration baseline.

That result does not mean invalidation has no performance cost. It means the cost was absorbed by the asynchronous pipeline and did not move the measured request latency tail during the period we evaluated.

## The measured result

We compared stale-read rates over four weeks before and after the migration using the same request-level measurement approach.

| Metric | TTL-based expiry | Event-driven invalidation |
|---|---:|---:|
| Stale reads | 3.1% of requests | 0.04% of requests |
| Request p99 latency | 41 ms | 41 ms |
| Peak invalidation throughput | Not applicable | 1,200 events/s on sale day |

The reduction from 3.1% to 0.04% was the primary reason for the change. We did not optimize for a theoretical consistency guarantee; we optimized for materially reducing the number of requests that could observe a value known to be outdated.

The remaining 0.04% is also useful. It tells us that event-driven invalidation eliminated most stale reads but did not eliminate every propagation gap. The remaining cases include the expected effects of short races, delayed processing, instrumentation boundaries, and failures that are retried successfully after the first read.

A percentage this small should not be treated as proof that the cache is always current. It is a production measurement under a defined workload and observation method.

## What we would do differently

The migration was successful, but there are several things we would improve if starting again.

### Define freshness requirements by field

We initially treated the product object as one cacheable unit. In reality, different fields have different freshness requirements. Price and availability deserve stricter propagation and monitoring than long-form descriptions.

A field-level freshness policy would help us decide which updates should invalidate which representations and which changes can tolerate asynchronous refresh.

### Design observability before the consumer

It is difficult to diagnose stale data if the system cannot answer:

- When was the source updated?
- When was the event created?
- When was it delivered?
- When was the cache key invalidated?
- When was the next value filled?

We added much of this instrumentation during the rollout. Building it first would have shortened the investigation of several early discrepancies.

### Test races deliberately

Most functional tests covered the straightforward sequence of write, event, invalidation, and read. The hardest bugs appeared in interleavings involving concurrent reads and updates.

A better test plan would include deterministic scenarios for:

- Cache fill concurrent with invalidation
- Duplicate events
- Out-of-order events
- Consumer restart during processing
- Queue delay followed by a bulk update
- Cache failure during invalidation
- Partial event publication

### Keep the TTL fallback

It is tempting to remove TTLs after event-driven invalidation is working. We kept them, and that was the right decision. A fallback expiration does not replace invalidation, but it bounds the lifetime of an entry when the event path fails.

The fallback TTL also provides a recovery mechanism for bugs in key mapping or events that cannot be processed.

## The broader lesson

TTL expiration is a good default when freshness is approximate and the system does not have a reliable change signal. It is simple, easy to reason about, and often sufficient.

It becomes a poor fit when:

- Updates are already represented as durable events.
- Some fields must become fresh quickly.
- The cost of stale reads is visible to users or downstream systems.
- Traffic and update patterns are bursty.
- A fixed expiration window forces an uncomfortable freshness-versus-load trade-off.

Event-driven invalidation did not remove distributed-systems complexity from our catalog. It made that complexity explicit in a place where we could measure and operate it.

The key design choices were straightforward:

1. Publish invalidation events only after the source-of-truth write is durable.
2. Make invalidation idempotent.
3. Prefer deleting and refilling over duplicating cache-construction logic.
4. Protect against stale cache fills racing with updates.
5. Retain TTL as a safety net.
6. Monitor propagation delay, not just queue depth.
7. Measure stale reads directly.

For our product catalog, those choices reduced stale reads from **3.1% to 0.04%** without changing the **41 ms p99 latency** we had worked to maintain. The invalidation queue peaked at **1,200 events per second** during our busiest update burst, and the system continued to serve requests within the same latency envelope.

That was the trade we wanted: more explicit infrastructure in exchange for data that is much more likely to reflect what the catalog actually says.
