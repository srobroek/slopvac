# Why We Switched to Event-Driven Cache Invalidation

Our product catalog cache was leaking stale data at a rate we could not accept. After running a four-week pilot of event-driven invalidation, we cut stale reads from 3.1% of requests to 0.04%, with no change to p99 latency. We shipped the change to production.

## The Problem

Our catalog service cached product information with a 5-minute TTL. The cache served 40,000 requests per second at peak, so the latency cost of a miss was high—we needed to keep the hit rate above 99%. The TTL strategy solved the latency problem but created a reliability problem: a price change, stock update, or product metadata edit took up to 5 minutes to reach users' screens. At 3.1% stale reads, roughly 1,200 requests per second served outdated data during normal traffic.

This mattered. A user could add an item to their cart at an old price, wait for checkout, and see a surprise. A shopper could see "out of stock" after the item had been restocked. The catalog service owned this problem because other services depended on us to tell the truth about the catalog.

We explored three paths: raise the TTL and accept more staleness, lower the TTL and pay the latency cost on misses, or listen to state changes and invalidate the cache only when the data actually changed. We chose the third.

## The Solution

We built a simple event pipeline. When a catalog mutation happened—a price change, a stock update, a product created—the mutation service published an event to a Kafka topic. The cache service consumed those events and evicted the relevant cache entries. On the next request for that entry, the cache would miss and fetch fresh data from the database.

We deployed a second consumer group to measure the tail latency of invalidation messages. Most events invalidated the cache within 500 microseconds of arrival. The 99th percentile was 12 milliseconds. This meant the delay between a mutation and a cache miss was bounded and observable.

The queue depth spiked on sale days. When we launched a flash sale, the inventory service published 1,200 invalidation events per second. The pipeline held at that throughput without dropping events. We confirmed by checking that the number of events ingested by the cache service matched the number published by the inventory service, with no unacknowledged messages in the consumer lag metric.

## The Results

Over four weeks, stale reads fell to 0.04% of requests. The remaining 0.04% came from two sources: requests that arrived during the window between a mutation and the event's arrival at the cache (a few milliseconds), and a small number of database read replicas that lagged behind the primary. We treated both as acceptable.

The p99 latency stayed at 41 milliseconds. We had feared that higher cache-miss rates would increase latency, but the miss rate rose only slightly—from 0.5% to 0.7%—because invalidation was now targeted. With the TTL approach, every cache slot expired after 5 minutes whether the data changed or not. With event-driven invalidation, only changed data triggered a miss.

We measured the end-to-end latency from mutation to cache invalidation by logging timestamps at the mutation service and the cache service and joining them by request ID. The median latency was 8 milliseconds. The 99th percentile was 280 milliseconds (driven by occasionally slow Kafka brokers, not our code). We committed to monitor this metric going forward and alert if the 99th percentile crossed 500 milliseconds.

## What We Kept and Changed

We kept the cache. We kept the 5-minute TTL as a safety net: if the event pipeline failed silently, the TTL would eventually evict stale data instead of serving it forever. We changed the invalidation strategy from "forget everything periodically" to "forget only what changed."

We did not add background refresh. A common approach is to update the cache after invalidation, fetching fresh data and re-populating the slot. We chose to let misses refetch on demand because the catalog database answered reads in single-digit milliseconds and our traffic is bursty. Refreshing everything would waste database load during quiet periods.

## Operational Posture

We get alerts if the invalidation topic's consumer lag exceeds 10 seconds, which would mean the cache service fell behind. Lag has stayed at 0 since we shipped. We get alerts if the p99 latency of invalidation exceeds 500 milliseconds. We track the stale-read rate as a metric in our dashboard and review it weekly.

We added one new failure mode: if the Kafka brokers fail or the cache service loses its consumer group, invalidation stops and the TTL becomes the only guard against staleness. We mitigated by running Kafka with three brokers across three availability zones and by making the cache service restart automatically if it cannot reach the brokers.

## What We Learned

The 5-minute TTL seemed like a constant until we measured staleness. Once we knew 3.1% of reads were stale, the choice to build an event pipeline was straightforward. Measuring the baseline unlocked the decision.

Event-driven invalidation scaled to our peak load without code changes. The 1,200 events per second on a sale day required no special handling. Kafka and our consumer handled it in stride. If load grew further, we would partition the topic, but we have headroom.

A common misconception is that event-driven invalidation is simpler than TTL invalidation. It is not. We added a message queue, a second consumer, monitoring on queue depth and lag, and a failure mode. We paid this cost because the staleness rate made it worth it. For a different service where 3.1% stale reads were tolerable, the TTL strategy is the right call.
