# Why We Ditched TTL-Based Cache Expiry for Event-Driven Invalidation

For the last two years, our product catalog cache ran on a simple, boring rule: every entry expired after 60 seconds. Boring is usually good for infrastructure, but in this case "boring" was quietly costing us correctness. This post covers why we moved from TTL expiry to event-driven invalidation, what it took to build, and what changed in production over a four-week rollout.

## The problem with TTLs

Our catalog cache sits in front of the product database and serves price, inventory, and metadata for every storefront request. With a 60-second TTL, every cache entry is a bet: we're betting that whatever changed upstream in the last minute either didn't happen or doesn't matter. During normal traffic, that bet mostly paid off. During a flash sale, a price correction, or a bulk inventory update, it didn't.

Concretely, we saw three recurring failure modes:

- **Price/inventory drift.** A price change or a stock-out could take up to 60 seconds to reflect in the cache, which is an eternity when a sale starts on the hour and thousands of concurrent shoppers hit the same SKU.
- **Cascading staleness on writes.** Bulk catalog updates (vendor feed imports, merchandising batch jobs) would touch thousands of rows at once, but the cache had no idea any of that happened until each entry's individual TTL ran out — so staleness wasn't evenly distributed, it clustered right after big writes.
- **No correctness signal.** TTL expiry tells you nothing about *whether* the underlying data changed. We were paying the cost of a stale read regardless of whether 0% or 100% of expired entries were actually out of date.

We measured stale reads directly by comparing served cache values against the source of truth on a sampled basis, and found we were sitting at **3.1% stale reads** — well above what our fraud, pricing, and merchandising teams considered acceptable.

## Why not just shrink the TTL?

The obvious first move is to lower the TTL. We tried it. Dropping to 15 seconds cut staleness modestly but drove cache hit rate down and database load up, without addressing the core issue: TTLs only bound *how long* staleness can last, they don't detect *whether* it exists. We wanted to invalidate a cache entry the instant the underlying data changed, and only then — not on a timer that had no relationship to actual write activity.

## The design: event-driven invalidation

We already had a change data capture (CDC) stream off the product database (Debezium reading the Postgres WAL into Kafka), originally built for analytics. Instead of adding a separate polling mechanism, we repurposed that stream as the invalidation trigger:

1. **Write happens** in the catalog service (price update, inventory adjustment, metadata edit, bulk import row).
2. **CDC captures the change** at the WAL level and emits an event keyed by product ID and changed fields.
3. **An invalidation consumer** reads the stream, maps the change to affected cache keys (a single product can back multiple cache entries — by locale, by channel, by aggregation), and issues targeted `DEL`/`UNLINK` calls to Redis.
4. **The next read** for that key is a clean cache miss, refilled from the database on demand.

A few implementation details mattered more than we expected:

- **Fan-out mapping.** A single row change can invalidate several cache keys. We maintain an explicit mapping table (product ID → derived cache key patterns) rather than trying to infer it from the event payload, because implicit mapping logic turned into a debugging nightmare during code review.
- **Idempotent consumers.** CDC streams can redeliver. Invalidation is naturally idempotent (deleting an already-deleted key is a no-op), which made this an easy property to lean on rather than fight.
- **Backpressure isolation.** We put the invalidation consumer on its own consumer group with its own scaling policy, separate from the analytics consumers on the same topic, so a slow analytics sink can never delay invalidation.
- **`UNLINK` over `DEL`.** For large hash/set-backed cache entries, `UNLINK` avoids blocking the Redis event loop on deletion, which matters when invalidation volume spikes.
- **Fallback TTL as a safety net.** We kept a long TTL (30 minutes) as a backstop in case an invalidation event is ever dropped or a mapping bug leaves an entry unaddressed. It's a safety net, not the primary mechanism — belt and suspenders, not two belts.

## Results after four weeks

We rolled this out gradually — shadow mode first (invalidations computed and logged but not applied), then live on a percentage of cache keys, then fully live — and tracked three numbers closely.

**Stale reads: 3.1% → 0.04%.** This is the headline number and the whole point of the project. The remaining 0.04% is almost entirely accounted for by the fallback-TTL window catching the rare dropped or delayed event, which is exactly the behavior we designed for.

**p99 latency: unchanged at 41 ms.** This was the result we were most nervous about walking in — we half-expected event-driven invalidation to trade staleness for either extra latency (more cache misses to fill) or extra volatility (invalidation storms causing thundering-herd refills). Neither materialized. Hit rate dipped only slightly because invalidations are now precise rather than blanket, so we're not throwing away cache entries that were never touched. p99 held steady at 41 ms across the rollout.

**Invalidation queue peak: 1,200 events/sec on a sale day.** This is the number that told us the architecture would hold up under real load, not just steady-state traffic. A flash sale drives a burst of price and inventory writes, and our invalidation consumer group absorbed a peak of 1,200 events/sec without a backlog forming or invalidation latency (event-to-cache-clear time) drifting past our SLO of under 500 ms. We deliberately over-provisioned consumer parallelism ahead of that sale specifically to validate this, and it held.

## What we'd do differently

If we were starting from scratch, we'd build the fan-out mapping table before writing a single line of consumer code — we underestimated how much of the complexity in this project was really a data-modeling problem (which writes affect which cache keys) rather than a streaming problem. We'd also instrument stale-read sampling from day one instead of retrofitting it; having the 3.1% baseline in hand made every subsequent decision easier to justify and easier to validate against.

## Should you do this?

Event-driven invalidation isn't a universal upgrade over TTLs — it adds a moving part (the CDC/invalidation pipeline) and requires accurate change-to-key mapping, which is real ongoing maintenance. It's the right trade when your staleness cost is high (pricing, inventory, anything customers can catch you being wrong about) and you already have or can justify a change stream. If your cached data is low-stakes or changes rarely, a well-tuned TTL is probably still the simpler and correct choice. For us, with a catalog that changes constantly and a business that notices every stale price, it was worth the added complexity — and the numbers back that up.
