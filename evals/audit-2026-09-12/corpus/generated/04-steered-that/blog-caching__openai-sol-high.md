# Why we replaced TTL expiry with event-driven catalog invalidation

Our engineering team replaced TTL-based expiry because catalog mutations, not elapsed time, determine when cached product data becomes stale.

Over four weeks, stale reads fell from 3.1% to 0.04% of requests. P99 latency remained 41 ms.

## The TTL failure mode

TTL expiry allowed each cached record to remain readable until its timer expired. A successful catalog mutation did not remove the corresponding cache entry.

Requests arriving before expiry could receive the previous record. Longer TTLs increased this stale-read window.

Shorter TTLs reduced the window but caused more requests to repopulate expired entries. TTL tuning could only move the tradeoff between freshness and cache retention.

## The event-driven path

Our catalog write path publishes an invalidation event after each successful mutation. The event identifies the affected cache key.

A queue consumer receives the event and removes the corresponding entry. The next read loads the updated record and repopulates the cache.

The read path does not wait for queue processing. Reads retain the same cache lookup behavior while invalidation runs asynchronously.

```text
Catalog mutation
       |
       v
Invalidation event
       |
       v
Queue consumer
       |
       v
Cache key removal
```

## Four-week results

| Metric | TTL expiry | Event-driven invalidation | Change |
|---|---:|---:|---:|
| Stale reads | 3.1% | 0.04% | 3.06 percentage-point reduction |
| P99 latency | 41 ms | 41 ms | No measured change |
| Peak invalidation input rate | Not applicable | 1,200 events per second | Sale-day peak |

The stale-read rate decreased by 98.7% relative to the 3.1% TTL baseline. The remaining 0.04% shows that asynchronous invalidation does not eliminate every stale read.

P99 latency remained 41 ms under both designs. We improved freshness without adding queue work to the read path.

The invalidation queue’s input rate peaked at 1,200 events per second on a sale day. We use that measured peak as the minimum baseline for consumer capacity tests.

## The operational tradeoff

Event-driven invalidation replaces timer tuning with queue operations. Event publication, delivery delay, and consumer throughput now affect cache freshness.

Invalidation must remain idempotent because deleting an absent cache key should produce the same result as deleting it once. Consumers must also sustain 1,200 events per second without accumulating sale-day lag.

Queue monitoring must cover input rate, consumer throughput, queue depth, and oldest-event age. An increasing oldest-event age indicates that stale entries can remain readable longer.

## The decision

TTL expiry removes an entry after a configured duration. Event-driven invalidation removes an entry after the catalog mutation makes it obsolete.

That distinction matched our product catalog’s freshness requirement. Over four weeks, it reduced stale reads from 3.1% to 0.04% while keeping p99 latency at 41 ms.
