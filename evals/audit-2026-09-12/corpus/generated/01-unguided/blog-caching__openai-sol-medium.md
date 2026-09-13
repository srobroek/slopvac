# Why We Replaced TTL-Based Catalog Caching With Event-Driven Invalidation

Caching our product catalog gave us predictable read latency, but time-to-live expiry also created a predictable correctness problem: after a product changed, customers could see stale data until its cache entry expired.

That tradeoff became increasingly difficult to justify. Prices, availability, promotions, and product status can change at any time, and some of those changes need to reach customers immediately. Shortening the TTL reduced the stale window but increased cache misses and backend load. Lengthening it improved cache efficiency while making stale reads last longer.

We replaced TTL-based expiry as our primary consistency mechanism with event-driven invalidation. Over the first four weeks after rollout:

- Stale reads fell from **3.1% to 0.04% of requests**.
- **p99 latency remained unchanged at 41 ms**.
- The invalidation queue peaked at **1,200 events per second** during a sale day.

This post explains the design, the failure modes we planned for, and why we retained TTLs as a safety net rather than removing them entirely.

## The problem with TTL as a consistency mechanism

Our catalog read path followed a conventional cache-aside pattern:

1. Look up the product in the cache.
2. Return it on a cache hit.
3. On a miss, read from the catalog datastore.
4. Populate the cache with a fixed TTL.

The design was simple and operationally inexpensive. It also meant that a successful catalog update did not update cached representations. The system waited for each affected entry to expire.

That behavior caused several problems.

### Staleness was unrelated to business importance

A routine description edit and an urgent product deactivation had the same propagation behavior. Both remained stale for as long as the remaining TTL allowed.

The cache did not know that one change was cosmetic while another could affect whether an item should be sold.

### TTL tuning forced the wrong tradeoff

Reducing the TTL shortened the maximum stale period, but it also lowered the hit rate. More requests reached the datastore, and popular entries were repopulated repeatedly even when their data had not changed.

Increasing the TTL reduced datastore traffic but extended the period during which customers could receive outdated responses.

There was no single TTL that was appropriate for both performance and correctness.

### Cache popularity affected convergence

Popular products usually refreshed soon after expiry because another request repopulated them. Less frequently accessed products could remain stale until their next read discovered the expired entry.

Expiry determined when an entry became invalid, but request traffic determined when it converged on the latest state.

### Related cache entries expired independently

A single product update could affect several cached views:

- The product detail response
- Category or collection listings
- Search result fragments
- Promotion eligibility
- Availability summaries

With TTL-only expiry, these entries refreshed on separate schedules. Customers could therefore see internally inconsistent views of the same product.

## The event-driven design

The key change was to connect catalog writes to cache invalidation.

When a catalog mutation commits, the write path records an event describing the changed entity and its version. A publisher sends that event to a durable queue. Invalidation workers consume the event, derive the affected cache keys, and delete those entries.

The next read repopulates each deleted entry from the source of truth.

```text
Catalog write
     |
     v
Datastore commit + durable event record
     |
     v
Event publisher
     |
     v
Invalidation queue
     |
     v
Invalidation workers
     |
     +--> Delete product cache key
     +--> Delete listing cache keys
     +--> Delete derived-view cache keys
```

We chose invalidation instead of pushing new values into the cache. Deletion keeps one authoritative read path: cache misses are filled using the same logic whether they result from expiry, eviction, or a catalog change. It also avoids reproducing view-building logic in the event consumer.

## Publishing events without losing writes

The most important correctness requirement was preventing this sequence:

1. The catalog update commits.
2. Event publication fails.
3. The cache remains stale until its TTL expires.

Publishing directly to the queue from application code would leave a gap between the datastore transaction and the queue operation. We therefore used a transactional outbox: the catalog change and an event record are written in the same transaction.

A separate publisher reads committed outbox records and sends them to the invalidation queue. If publication fails, it retries. This gives us at-least-once delivery without requiring a distributed transaction between the datastore and the queue.

At-least-once delivery means consumers can receive duplicate events. Cache deletion is naturally idempotent, so processing the same invalidation more than once is safe.

## Handling ordering and concurrent reads

Deleting cache entries sounds straightforward, but concurrency introduces less obvious failure modes.

Consider this sequence:

1. A request misses the cache and starts reading product version 41.
2. The product is updated to version 42.
3. The invalidation event deletes the cache entry.
4. The original request finishes and writes version 41 back into the cache.

Without another safeguard, an old request can repopulate stale data after invalidation.

We addressed this by associating cached values and change events with entity versions. Cache population uses a conditional write so that an older version cannot replace a newer known version. Workers also ignore events older than the latest version they have already processed for that entity.

Versioning makes invalidation robust to:

- Duplicate delivery
- Out-of-order events
- Retries
- Concurrent cache fills
- Delayed consumers

It also gives us useful diagnostic information. When we detect a stale response, we can compare the cached version, source version, and latest processed event instead of relying only on timestamps.

## Invalidating derived views

The product key was only part of the problem. Catalog data appeared in several derived views, some of which did not map cleanly to one product identifier.

We added an explicit dependency model that maps change types to affected cache namespaces. For example, a price change may invalidate the product detail entry, applicable collection pages, and promotion-derived data. A description change may affect fewer views.

We avoided broad cache flushes. Clearing an entire namespace is easy to implement, but it can create a cache-miss surge and place sudden load on the datastore. Our workers instead compute targeted keys wherever practical.

Some dependencies are too expensive to enumerate synchronously. For those, we use generation identifiers. A cache key includes the current generation for a logical collection; incrementing that generation makes existing entries unreachable without deleting every key individually.

## Why we kept TTLs

Event-driven invalidation is now our primary freshness mechanism, but cached entries still have TTLs.

The TTL is no longer our expected propagation path. It is a backstop for cases such as:

- A malformed event that cannot be processed
- An undiscovered dependency missing from the invalidation map
- Extended queue or worker failure
- Operational mistakes during deployment
- Orphaned keys from an older cache-key format

This distinction matters. Under the old design, every update was expected to remain stale until expiry. Under the new design, expiry limits the impact of exceptional failures.

Retaining TTLs also bounds cache growth and lets us recover without requiring a perfect inventory of every historical key.

## Backpressure and sale-day traffic

Moving to events introduced a new capacity concern: invalidation volume scales with catalog mutation volume.

During a sale day, the invalidation queue peaked at **1,200 events per second**. The system absorbed that peak without affecting the product read path because event processing is asynchronous and workers scale independently from request-serving instances.

We monitor more than queue throughput. The more important signals are:

- Age of the oldest unprocessed event
- End-to-end time from datastore commit to cache deletion
- Queue depth
- Consumer retry rate
- Dead-letter volume
- Invalidation operations per event
- Cache miss rate after invalidation bursts
- Datastore load caused by repopulation

Queue depth alone can be misleading. A large queue may be healthy if consumers are keeping event age low, while a smaller queue can indicate a serious problem if one partition or entity key is blocked.

We also use retry limits and a dead-letter queue so that a malformed event cannot prevent later events from being processed indefinitely. Dead-lettering is paired with alerts and replay tooling; otherwise it merely turns visible failures into silent staleness.

## Rolling it out safely

We did not switch the write path and assume the new design worked. We rolled it out in stages.

First, we emitted events and processed them in observation mode without deleting cache entries. This let us validate event coverage, key derivation, ordering behavior, and expected throughput.

Next, we enabled invalidation for a subset of catalog entities and compared cached responses with the source of truth. We tracked stale reads by entity type and change type, which helped identify missing dependencies.

We then increased traffic gradually while watching:

- Stale-read rate
- Cache hit rate
- Catalog datastore load
- Read latency
- Event processing lag
- Consumer errors

Finally, we retained the previous TTL settings during the initial rollout. That bounded the impact of missed invalidations while we established confidence in the event path.

## Results after four weeks

The main objective was to reduce stale reads without degrading read performance.

| Metric | TTL-based expiry | Event-driven invalidation |
|---|---:|---:|
| Stale reads | 3.1% of requests | 0.04% of requests |
| p99 latency | 41 ms | 41 ms |
| Peak invalidation rate | Not applicable | 1,200 events/second |

Stale reads fell by more than 98% relative to the previous rate. The remaining **0.04%** includes propagation windows, detected failure cases, and races that our measurement catches before convergence.

Just as importantly, **p99 latency remained at 41 ms**. We kept invalidation work off the synchronous read path, and targeted deletion avoided the miss storms that broad cache flushes could have caused.

The sale-day peak showed that the queue and consumers could handle substantial mutation bursts. It also gave us a real workload for validating autoscaling, lag alerts, retries, and datastore behavior during cache repopulation.

## Costs and tradeoffs

Event-driven invalidation improved freshness, but it did not make the system simpler.

We now operate:

- An outbox publisher
- A durable queue
- Invalidation workers
- Dependency and key-derivation logic
- Retry and dead-letter handling
- Version-aware cache writes
- Queue-lag and propagation monitoring
- Replay and reconciliation tools

The cache is also only eventually consistent. Event-driven invalidation shortens the stale window substantially, but it does not make cache updates atomic with catalog writes. Workflows requiring read-after-write consistency still bypass the cache or use version-aware reads.

Correctness also depends on complete event coverage. If a new derived view is added without its invalidation dependency, TTL expiry may be the only mechanism that eventually refreshes it. We treat cache dependencies as part of a feature’s design and test them alongside the write path.

## What we learned

Several principles from this migration apply beyond product catalogs.

### TTL is useful, but weak as the primary freshness policy

TTL expiry is an effective fallback and resource-management tool. It is less effective when the acceptable stale period depends on a business event rather than elapsed time.

### Reliable event publication matters more than fast consumers

Consumer throughput is visible and easy to benchmark. The harder failure is a committed change that never produces an event. A transactional outbox closed that gap for us.

### Invalidation must account for repopulation races

Deleting a key does not prevent an older in-flight request from restoring stale data. Versions or another form of conditional cache population are necessary when correctness matters.

### Dependency tracking is part of the data model

Derived cache entries must be connected to the entities and change types that affect them. Treating this mapping as explicit system behavior made it testable and observable.

### Keep an independent repair mechanism

TTLs, reconciliation jobs, and event replay each cover different failure modes. Event-driven invalidation should reduce reliance on expiry, not remove every recovery path.

## Closing perspective

TTL-based caching optimized for simplicity, but it made staleness an expected part of every catalog update. Event-driven invalidation changed that model: catalog changes now trigger convergence, while TTL expiry handles exceptions.

After four weeks, stale reads dropped from **3.1% to 0.04%**, p99 latency held at **41 ms**, and the system handled a peak of **1,200 invalidation events per second** during a sale day.

The migration added infrastructure and operational responsibility. For catalog data—where price, availability, and product status can change quickly—that complexity bought us a much stronger relationship between a committed update and what customers see.
