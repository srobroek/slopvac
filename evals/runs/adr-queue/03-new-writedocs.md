# ADR 0012: Use a managed queue instead of self-hosting one

- Status: Accepted
- Date: 2026-03-11
- Deciders: Ana Reis, Tom Halvorsen

## Context

The order service hands work to an async worker: invoice rendering, email, and webhook fan-out. Expected volume is 2 million messages per month, with a peak of 400 messages per second during a daily 20-minute batch.

Constraints that decided this:

1. Two engineers maintain the whole system, including on-call. There is no platform team.
2. We already run in one AWS account, `prod-eu-central-1`, with the workers in three availability zones.
3. A single-zone outage must not lose an accepted message and must not stop delivery. This comes from the SLA in `contracts/enterprise-tier.md`, which promises order confirmation within 15 minutes.

## Decision

We use Amazon SQS. Standard queues for webhook fan-out, one FIFO queue for invoice numbering, and a dead-letter queue after 5 receives.

## Consequences

- SQS replicates each message across the three availability zones of `eu-central-1`. A zone outage costs no messages and needs no action from us, which satisfies constraint 3.
- No broker to patch, size, or fail over. Constraint 1 holds.
- At 2 million messages per month the bill is about 0.80 EUR per month, on the 1-million-request free tier plus 0.40 EUR per million requests.
- SQS delivers at least once on standard queues. Every consumer must be idempotent on the message's `id` field. This is the cost we accept in exchange for point 1.
- Maximum message size is 256 KiB. Payloads above that go to S3 and travel as a key. Invoice PDFs already work this way.
- Maximum in-flight messages per standard queue is 120,000. At the 400 per second peak with a 30-second visibility timeout, in-flight peaks near 12,000, which leaves a factor of 10.
- SQS has no message ordering on standard queues and no topic-based routing. Fan-out to more than one consumer needs SNS or EventBridge in front.
- The queue is reachable only from AWS credentials in `prod-eu-central-1`. Local development runs ElasticMQ, which is a second implementation to keep in step.

## Alternatives considered

### Self-hosted RabbitMQ on EC2

Rejected on operational load. A zone-tolerant setup needs a 3-node quorum-queue cluster across three availability zones, which the two of us would patch, monitor, upgrade, and fail over. Our previous RabbitMQ cluster in the billing service produced 4 of the 9 pages in the 2025 on-call log, all of them node or disk-alarm related. Constraint 1 cannot absorb that.

### Confluent Cloud Kafka

Rejected on cost at our volume. The smallest multi-zone Basic cluster bills a base charge plus throughput, which came to about 380 EUR per month in the March 2026 pricing calculator for 2 million messages and 3 partitions. That is 475 times the SQS figure for the same volume. Kafka's replay and ordering would matter above roughly 50 million messages per month; we are two orders of magnitude below that.

## Revisit when

- Monthly volume passes 50 million messages, where Kafka's per-message cost drops below SQS.
- A consumer needs to re-read a stream from an offset. SQS deletes an acknowledged message and cannot replay it.
- We add a second cloud provider, which would make an AWS-only queue a coupling point.
