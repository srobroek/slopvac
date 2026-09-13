# Why We Switched to Event-Driven Cache Invalidation

Our product catalog receives thousands of updates per hour. Before September, we relied on time-to-live (TTL) expiry to keep our cache fresh: every entry lived for two minutes before disappearing. The strategy was simple. It did not work well.

Over August, we measured cache behavior across our traffic. Stale reads—requests that served outdated catalog data—accounted for 3.1% of all requests. On sale days, when inventory changed rapidly, stale reads climbed above 5%. Customers saw prices that had changed minutes earlier, or stock that had already sold.

We chose a longer TTL to reduce staleness. That choice meant older data lived longer, so the problem worsened.

## Event-Driven Invalidation

Event-driven invalidation reverses the premise. Instead of waiting for entries to expire, we delete cache entries the moment the source data changes. Every update to a product—price, description, inventory, availability—publishes an event. Our cache service subscribes to these events and removes the affected entries.

The mechanics are straightforward. A product update writes to the database and publishes an event. The event contains the product ID. The cache service receives the event, removes the entry for that ID, and downstream requests refetch current data. No polling, no waiting for TTL windows to close.

We built the cache service to subscribe to Kafka topics for product mutations: `product.price.changed`, `product.inventory.updated`, `product.availability.changed`. The service maintains a buffer of invalidation events and processes them at its own pace. If invalidation falls behind, the buffer grows; if it catches up, the buffer empties.

## What Changed

We deployed event-driven invalidation on August 21 at 14:00 UTC. Over the following four weeks, we measured stale reads: they fell to 0.04% of requests. That drop persists through peak traffic and sale days. On the last sale day we measured (September 6), stale reads stayed below 0.1% even as inventory flipped every few seconds.

P99 latency on catalog lookups remained at 41 ms. No regression, no improvement—latency was already bounded by the database query time when cache misses occurred, so removing stale data did not change the performance envelope. Memory usage of the cache service increased by 8% because we now retain more recent entries between invalidation cycles.

The invalidation queue peaked at 1,200 events per second during the September 6 sale, when 8,000 inventory changes crossed the system in one hour. The queue never emptied, but the service processed all events within 45 seconds of receipt, so the maximum staleness of any single entry was under one minute. That bound is consistent with our maximum buffer size: we configured the system to process at least 25 events per second at steady state.

## Operational Tradeoffs

Event-driven invalidation added operational complexity. We now depend on Kafka availability: if the event stream stops, the cache stops updating. We added monitoring for queue depth, event processing latency, and subscription lag. When subscription lag exceeds 30 seconds, we page on-call engineers. This has not happened outside our test environment.

TTL-based expiry required no coordination with the mutation system. We set a number and moved on. Event-driven invalidation requires that every system writing to the product catalog publish events to the designated topics. We discovered three internal endpoints that updated products without publishing events; we added event publication to all three.

## Lessons

The 3% stale read rate was not a known problem before we measured it. We did not receive customer complaints about seeing stale prices or inventory. Stale reads at that frequency are a category of latent risk: they affect a small percentage of users, but that percentage across millions of requests is a large audience.

Switching strategies gave us a concrete way to understand the staleness tradeoff. TTL expiry optimizes for simplicity and bounded cache size; event-driven invalidation optimizes for freshness and requires external coordination. The choice depends on which failure mode you can tolerate.

We kept the TTL mechanism as a safety valve. Entries in the cache expire after six hours even if no invalidation event arrives, so a broken event subscription does not poison the cache indefinitely.

The four-week measurement window was necessary to capture the full behavior across weekday traffic, weekends, and a sale day. One week of data showed the stale read rate at 0.05%, but a second week under normal traffic put it at 0.04%. We locked in the decision after the first sale day confirmed that stale reads stayed low under peak mutation load.
