# Why we replaced TTL cache expiry with event-driven invalidation

Our product catalog cache used TTL-based expiry: every entry expired after a fixed window, regardless of whether the underlying data had changed. This post covers why we moved to event-driven invalidation and what changed over a four-week measurement period after the switch.

## The problem with TTL expiry

A TTL cache serves stale data for up to the length of the TTL window after a write, because the cache has no way to know a write happened. Before the switch, our catalog cache showed a 3.1% stale-read rate against production traffic. Every price update, inventory change, or listing edit had to wait out the TTL before shoppers saw the new value.

Lowering the TTL reduces staleness but increases load on the origin database, because more requests miss the cache and fall through to a live lookup. We were already tuning the TTL down for high-churn categories, and it was not solving the underlying issue: the cache had no signal that data had changed.

## The switch to event-driven invalidation

We connected the catalog cache to the write path: every update to a product record now publishes an invalidation event to a queue, and a consumer evicts the corresponding cache key on receipt. The cache still carries a long TTL as a backstop against missed events, but eviction happens on write instead of on a timer.

This moves the correctness guarantee from "stale for at most T seconds" to "stale for at most the invalidation pipeline's delivery time." It also means cache misses now correlate with actual writes rather than with an arbitrary expiry schedule.

## Results after four weeks

We measured production traffic for four weeks after rollout and compared it against the same metrics under the previous TTL-based cache.

- Stale reads fell from 3.1% to 0.04% of requests.
- p99 latency was unchanged at 41 ms.
- The invalidation queue peaked at 1,200 events per second on a sale day.

The stale-read drop confirms that eviction is now tied to writes, not to a timer that runs independently of them. The unchanged p99 latency shows the added invalidation step did not slow down cache reads or writes on the request path. The 1,200 events/second peak occurred during a scheduled sale day with a high rate of catalog updates, and the invalidation consumers kept pace with that load without a backlog.

## What this means for teams evaluating the same move

If your cache serves data that changes on a predictable write path (a product catalog, a user profile store, a config service), event-driven invalidation lets you tie cache correctness to those writes directly. Keep a TTL as a backstop for missed or malformed events. Measure your invalidation queue's peak throughput against your write volume before rollout, so you know it can absorb your highest-traffic events.
