# Replacing TTL Expiry With Event-Driven Invalidation in the Product Catalog Cache

Our catalog read path served 3.1% of requests from a cache entry that no longer matched the database. We shipped event-driven invalidation four weeks ago, and that number is now 0.04%. This post covers why TTLs failed for us, what the new path looks like, and the two results that surprised us.

## What the TTL was actually buying us

The catalog read service fronts a Postgres catalog with Redis. Each entry is a fully rendered product document: title, media references, price, availability, and badge state. Building one requires three downstream calls, so the cache is load-bearing rather than a nice-to-have.

The original policy was a 60-second TTL with ±10% jitter. That number was picked in 2021 because it kept origin QPS inside what the pricing service could absorb, and nobody revisited it.

A TTL encodes one assumption: staleness bounded by 60 seconds is acceptable. That assumption held until merchandising started running flash sales with per-minute price-book activations, and until we added a "2 left in stock" badge. Both features are ones where a stale read is visible to the customer. A shopper adding an item at the pre-sale price, then seeing the sale price at checkout, files a support ticket. So does a shopper who buys the last unit of something we already sold.

Shortening the TTL was the obvious lever, and it is the wrong one. Going from 60s to 5s multiplies origin load by roughly twelve for a twelve-fold reduction in the staleness window. You pay continuously, in capacity, for a correctness property you need only at the moments data actually changes. Catalog documents change rarely: our write rate is about 1.4 changes per second at baseline against roughly 30,000 reads per second. TTL expiry throws away 99.99% of cache entries that were still perfectly good.

### How we measured staleness first

We did not want to argue about this from intuition, so we built the measurement before the fix. A sampling reader picks 1% of served responses, re-reads the same product from the primary through a bypass path, and compares the `version` column. Disagreement counts as a stale read. This runs continuously and is the number quoted throughout this post.

Baseline over the week before the change: **3.1% of sampled requests stale**, with the rate spiking above 9% during price-book activations. The distribution was not uniform. Staleness clustered hard on exactly the products people were looking at, because sale items are both the most-viewed and the most-mutated.

## The new path

Writes to the catalog now go through an outbox table in the same transaction as the row change:

```sql
BEGIN;
UPDATE products SET price_cents = 2499, version = version + 1
  WHERE id = $1;
INSERT INTO catalog_outbox (product_id, version, change_kind)
  VALUES ($1, (SELECT version FROM products WHERE id = $1), 'price');
COMMIT;
```

A CDC connector tails the outbox into a Kafka topic partitioned by `product_id`. An invalidation consumer reads that topic and deletes the corresponding Redis keys. Three decisions inside that sentence did most of the work.

**We delete, we do not write through.** An earlier prototype had the consumer rebuild the document and write it into Redis. That turns every invalidation into three downstream calls, converts a 1,200 events/sec burst into a 3,600 QPS load spike on the pricing service, and introduces a second writer that can race with a cache fill in progress. Deleting is idempotent and cheap. The next reader pays the fill cost, and only if anyone actually wants the product.

**Version numbers guard the fill.** Deleting a key is not sufficient, because a read that started before the delete can complete after it and write a pre-change document over a post-change gap. Fills are conditional on the version they observed:

```
KEY  product:{id}
VAL  {version, document}

fill(id, version, doc):
  existing = GET key
  if existing and existing.version >= version: return   # newer fill won
  SET key {version, doc}
```

Partitioning by `product_id` gives us per-product ordering in the topic, so the consumer never processes a product's version 8 before its version 7. Cross-product ordering does not matter to us.

**The TTL is still there, at six hours.** It is no longer the correctness mechanism; it is the backstop for a lost event. If the outbox row is written but the connector drops the message, unbounded staleness becomes six-hour staleness. We also have a replay tool that reads the outbox for a time range and re-emits, which we have used twice during connector upgrades.

## Bulk changes needed a separate answer

TTL jitter was doing something we had not accounted for: spreading misses out over time. A price-book activation touches about 40,000 SKUs. Under the old system those entries expired at 40,000 slightly different moments. Under event-driven invalidation, they are deleted within a few hundred milliseconds of each other, and every reader for a hot sale product arrives at an empty key simultaneously.

Two mitigations, both boring:

Single-flight per key in the read service. Concurrent misses for the same product wait on one in-flight fill rather than each calling downstream. This alone cut the post-activation origin spike by about 85%.

Per-key jitter for bulk events only. Events carrying `change_kind = 'price_book'` get a delay drawn uniformly from 0 to 1000 ms before the delete. Single-SKU edits, inventory decrements, and takedowns are processed immediately. This is a real tradeoff: it admits up to one second of staleness at a sale boundary, in exchange for not needing headroom for a 40,000-key stampede. We accepted it because the sale start time is announced to the second, not the millisecond, and because a takedown is the case where immediacy actually matters legally.

## Results, four weeks

| Metric | TTL (60s) | Event-driven | Change |
| --- | --- | --- | --- |
| Stale reads (1% sample) | 3.1% | 0.04% | −98.7% |
| p99 read latency | 41 ms | 41 ms | none |
| p50 read latency | 8.2 ms | 6.9 ms | −16% |
| Cache hit rate | 91.4% | 98.2% | +6.8 pts |
| Origin QPS, steady state | 2,580 | 540 | −79% |
| Invalidation events/sec, peak | n/a | 1,200 | — |
| Invalidation lag, p99 at peak | n/a | 240 ms | — |

The 1,200 events/sec peak came from a sale day with four staggered price-book activations. The consumer runs six partitions on three instances and stayed under 30% CPU, so we have not needed to tune it. Residual 0.04% staleness is consistent with the invalidation lag: a read that lands inside the 240 ms window between commit and delete is legitimately stale, and no amount of tuning removes that class entirely without synchronous invalidation on the write path.

**p99 did not move, and we expected it to.** The prediction was that cutting cache misses by 79% would pull in the tail, since a miss costs 30 to 60 ms and a hit costs under 2 ms. It did not, because our p99 was never dominated by misses. Profiling the slowest 1% showed the cost concentrated in response serialization for products with large variant matrices (some apparel items have over 400 variants) and in a retry against the media service that fires on about 0.8% of requests regardless of cache state. Misses were roughly 9% of traffic contributing to a tail already full of other things. p50 improved as predicted, which is the honest read: this change bought correctness and origin capacity, not tail latency.

If you are pitching a similar migration internally, do not promise a latency win. Promise the staleness number and the origin-load number, and measure the tail separately.

## What we would do differently

Build the staleness measurement first. Ours existed two weeks before the fix, and it settled three design arguments that would otherwise have been decided by whoever was most confident in the room.

Treat bulk mutations as a distinct event class from the beginning. We discovered the stampede problem in staging load tests, which was lucky; the fix was cheap only because we had not yet built anything on the assumption that all invalidations are equivalent.

Keep the TTL. Several reviewers asked why we did not remove it once events were in place. The answer is that the consumer, the connector, and Kafka are three new components that can each fail silently in a way that produces indefinitely stale data, and a six-hour ceiling costs us almost nothing in origin load. Event-driven invalidation is a latency optimization on top of expiry, not a replacement for it.
