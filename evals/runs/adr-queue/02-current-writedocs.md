# ADR 0014: Use a managed queue rather than self-hosting one

- **Status**: Accepted
- **Date**: 2026-07-30
- **Deciders**: Platform (2 engineers)
- **Supersedes**: none

## Context

The order pipeline needs a durable queue between the API and the fulfillment workers. Requirements:

- At-least-once delivery with per-message acknowledgement.
- Survive the loss of one availability zone without operator action.
- Expected steady volume: 40 messages per second, about 100 million messages per month. Peak measured during the March promotion: 260 messages per second for 20 minutes.
- Message size p99: 4 KB.

Constraints that decided this:

- The team is two engineers, both on the same on-call rotation, with no dedicated operations capacity. There is no second rotation to hand a broker to.
- An AWS account already carries the API, the database, and the workers. Adding a service inside it costs no new vendor review, no new billing relationship, and no new network path.
- The zone-outage requirement means any self-hosted option needs a multi-zone quorum, not a single node.

## Decision

Use Amazon SQS standard queues, one queue per pipeline stage, each with a dead-letter queue after 5 receives.

## Consequences

- Zone failure is handled by the service. SQS replicates across zones within the region, and no runbook step exists for it.
- No broker to patch, no disk to size, no quorum to reason about. The on-call surface is the queue depth alarm and the dead-letter queue alarm.
- Standard queues do not order messages and can deliver a message more than once. Every consumer must be idempotent on the message's business key. This is a real cost: three existing handlers need an idempotency table before they can move onto the queue.
- No message priority. A priority need is served by a second queue, not a header.
- Maximum message size is 256 KB, and maximum retention is 14 days. Payloads above 256 KB must move to S3 with the queue carrying a pointer.
- Cost at expected volume: about $40 per month for 100 million requests, before batching. Batching 10 messages per call reduces the request count tenfold.
- The queue is reachable only from inside the account's IAM boundary. A future external publisher needs an API in front of it.

## Alternatives

### Self-hosted RabbitMQ or Kafka on EC2

Rejected on operational load.

A multi-zone quorum needs 3 nodes minimum. That brings broker version upgrades, disk growth monitoring, certificate rotation, partition rebalancing (Kafka) or queue mirroring policy (RabbitMQ), and a documented recovery procedure for a lost quorum member. Each of those is a runbook two engineers must write, test, and be paged for.

The 260 messages per second peak is far below what one broker node handles, so this option buys no throughput headroom we need. It buys ordering and priority, which the pipeline does not require: order arrival is already unordered upstream.

### Amazon MSK (managed Kafka)

Rejected on cost at expected volume.

MSK bills per broker-hour, not per message. A 3-broker `kafka.m5.large` cluster across three zones is about $390 per month plus storage, against about $40 per month for SQS at 100 million messages. The pipeline's 40 messages per second uses a small fraction of that provisioned capacity, so the premium buys ordering, replay, and consumer groups, none of which the pipeline uses today.

Revisit this decision when any of the following becomes true:

- A consumer needs to replay a stream from an arbitrary offset.
- Two or more consumer groups need independent reads of the same stream.
- Sustained volume exceeds roughly 1 billion messages per month, where per-request pricing approaches provisioned-broker cost.
