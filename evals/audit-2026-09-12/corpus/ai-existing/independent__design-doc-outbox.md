# Design: Transactional Outbox and CDC for Order Service Event Publishing

Status: for review
Author: platform-data
Reviewers: order-service owners, streaming infra

## Context

`order-service` performs a dual write on every state transition. Inside the
request handler we commit a row to Postgres and then call
`kafkaProducer.send()` on `orders.events`. Neither operation is atomic with
respect to the other. If the process dies between them, or the broker is
unreachable after the commit succeeds, the database and the topic disagree
permanently.

We have measured this. Over the last 90 days a reconciliation job comparing
`orders` rows against the compacted topic found 1,412 orders present in Postgres
with no corresponding `OrderCreated` event, and 87 events on the topic whose
order row was rolled back. Downstream, `fulfilment` and `analytics-ingest` both
treat the topic as the source of truth, so a missing event means an order that is
never picked. Three of the last eight P2 incidents in this service trace back to
this gap.

The workaround today is a nightly sweeper that replays missing events by
scanning for orders updated in the last 24 hours. It publishes out of order and
cannot detect the reverse case.

## Goals

- Guarantee that an event is published if and only if its database transaction
  commits.
- Preserve per-order ordering on the topic.
- Keep the publishing path out of the synchronous request, so broker
  unavailability does not fail customer writes.
- Retire the nightly sweeper.

## Non-goals

- Exactly-once delivery to consumers. We are targeting at-least-once with
  idempotency keys; consumers already dedupe on `event_id`.
- Changing the event schema or the topic's partitioning key.
- Migrating other services off dual writes. We want one worked example first.
- Cross-service distributed transactions. This is not a saga proposal.

## Proposed design

### Outbox table

Add an `event_outbox` table in the same Postgres database and schema as `orders`:

| column | type | notes |
| --- | --- | --- |
| `id` | `bigserial` | monotonic, drives ordering |
| `event_id` | `uuid` | consumer dedupe key |
| `aggregate_id` | `text` | order id, becomes the Kafka message key |
| `event_type` | `text` | e.g. `OrderCreated` |
| `payload` | `jsonb` | serialized event body |
| `created_at` | `timestamptz` | `default now()` |

Handlers write the outbox row in the same transaction as the domain change.
The producer call disappears from the handler.

### CDC pipeline

We read the outbox with Debezium's Postgres connector in Kafka Connect, using
logical replication (`pgoutput`) against a dedicated replication slot. The
connector's `EventRouter` SMT unwraps the envelope so the message on
`orders.events` carries the raw `payload` as its value and `aggregate_id` as its
key. Key-based partitioning preserves per-order ordering because the WAL
delivers `event_outbox` inserts in commit order.

A periodic `DELETE FROM event_outbox WHERE id <= :lsn_id` job driven by the
connector's confirmed offset keeps the table small. Deletes produce WAL churn
but no topic traffic, since we filter to inserts only.

### Why CDC rather than polling the table

A poller is simpler to operate but reintroduces a correctness hazard: `bigserial`
values are allocated before commit, so a poller ordering by `id` can skip a row
whose transaction commits late. Working around that needs commit-timestamp
tracking or a `SELECT ... FOR UPDATE SKIP LOCKED` claim loop, at which point we
have hand-built a worse version of the WAL reader. We already run Kafka Connect
for two other pipelines, so the operational cost of Debezium is marginal for us.

## Alternatives considered

**Keep dual writes, add a retry queue.** Cheapest change. Does not fix the
crash-between-writes window, which is where most of our 1,412 gaps come from.

**Listen/notify plus an in-process publisher.** Avoids Connect. `NOTIFY` is
fire-and-forget and delivers nothing to a disconnected listener, so we would
still need the outbox scan as a backstop.

**Kafka transactions with a Postgres-side two-phase commit.** Technically
correct, requires XA support we do not have in the JDBC path, and couples
request latency to broker health.

**Log the events to the topic first and project into Postgres.** Inverts the
source of truth. Large rewrite of every read path in `order-service`; out of
scope.

## Risks

- **Replication slot growth.** An unconsumed slot pins WAL and can fill the
  primary's disk. We will alarm on `pg_replication_slots.confirmed_flush_lsn` lag
  above 5 GB and page on it, and document dropping the slot as the break-glass
  action.
- **Ordering across aggregates is not preserved.** Consumers relying on global
  order will break. We checked: neither current consumer does.
- **Duplicate publishes on connector restart.** Connect offsets are committed
  asynchronously, so a restart can replay. Consumer dedupe on `event_id` covers
  this; we will verify `analytics-ingest` actually enforces it.
- **Schema drift between handler and SMT config.** A new `event_type` needs no
  connector change, but a routing change does. Adding a contract test.

## Rollout

1. Ship the outbox table and dual-write to both outbox and producer. Topic
   traffic unchanged; outbox is shadow data.
2. Stand up the connector writing to `orders.events.shadow`. Run a differ
   comparing shadow against the live topic for two weeks. Success bar: zero
   missing events, ordering matches per key.
3. Point the connector at `orders.events`, remove the direct producer call, keep
   the sweeper running as a net.
4. After 30 clean days, delete the sweeper and its reconciliation report.

Rollback at any stage is restoring the producer call, behind a flag through
step 3.
