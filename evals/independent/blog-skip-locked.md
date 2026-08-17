# The weekend I deleted Redis from my job queue

I spent last Saturday and most of Sunday ripping Redis out of our background
job system and replacing it with a single Postgres table and one slightly
weird SQL clause. I went in expecting a slog and came out mildly annoyed that
I hadn't done it a year earlier.

Here's how it went, and the parts that bit me.

## Why I bothered

Our setup was the usual thing: Postgres for real data, Redis for the queue,
a worker pool pulling jobs with BRPOPLPUSH. It worked. It also meant every
job that touched the database had a transactional hole in the middle of it.

The pattern that finally broke me: a user submits an order, we write the row,
we enqueue the "send confirmation" job. If the transaction rolls back after
the enqueue, the job still fires and emails somebody about an order that
doesn't exist. If we enqueue after commit and the process dies in between,
the email never goes out. There is no ordering of those two writes that is
correct, because they're in two different systems.

You can paper over this with an outbox table. But once you've got an outbox
table in Postgres, you're maintaining a queue in Postgres *and* a queue in
Redis, and one of them is redundant. I picked the one to keep.

The other motivation was less noble: I was tired of two things to monitor,
two things to back up, two things to upgrade, and a Redis instance whose
persistence config nobody on the team could confidently explain.

## The whole implementation

The core of it is embarrassingly short:

```sql
UPDATE jobs
SET status = 'running', started_at = now(), worker_id = $1
WHERE id = (
  SELECT id FROM jobs
  WHERE status = 'pending' AND run_at <= now()
  ORDER BY priority DESC, run_at
  FOR UPDATE SKIP LOCKED
  LIMIT 1
)
RETURNING *;
```

`SKIP LOCKED` is the entire trick. Without it, two workers hitting this at
once means one of them blocks on the other's row lock, wakes up, and finds a
row that no longer matches its WHERE clause. With it, the second worker just
walks past the locked row and grabs the next one. No blocking, no contention,
no lost updates. It's been in Postgres since 9.5 and I have no idea why I
thought of it as an exotic feature.

Claim, work, then `UPDATE ... SET status = 'done'` in the *same transaction*
as the job's own side effects. That's the whole reason I did this. Enqueueing
is now an INSERT inside the caller's transaction, so it commits or vanishes
along with everything else. The dual-write problem doesn't get solved, it
stops existing.

## Things I got wrong first

**Ordering by anything expensive.** My first version ordered by a computed
priority score. The plan went from index scan to sort-the-world, and with
twelve workers polling every 200ms that was most of my CPU. A composite
index on `(status, priority DESC, run_at)` with a partial predicate on
`status = 'pending'` fixed it. Keep the ORDER BY matched to an index or
this whole approach falls apart under load.

**Forgetting dead workers.** Redis with a reliable-queue pattern gives you
in-flight recovery for free-ish. Here I had to write it: a `started_at`
timestamp, a heartbeat, and a reaper that flips anything running past its
lease back to pending. Roughly forty lines. Not free, but not hard, and now
I can actually see the stuck jobs in a table instead of guessing at Redis
internals.

**Bloat.** Every claim is an UPDATE, so every claim writes a dead tuple.
On a busy queue table autovacuum's default thresholds are far too lazy —
the table is tiny in row count but churns constantly, so a 20% scale factor
means it almost never triggers. I set a per-table `autovacuum_vacuum_scale_factor`
of 0.01 and moved on. Also: completed jobs go to a separate archive table
rather than living in the hot one forever.

**Polling latency.** Redis blocking pops give you near-instant pickup;
polling gives you your interval. I used `LISTEN`/`NOTIFY` on enqueue to wake
idle workers, with the poll loop as the fallback for anything NOTIFY misses.
Best of both, and NOTIFY being unreliable-by-design doesn't matter when
polling is your safety net.

## Would I recommend it

If you're already running Postgres and your queue does thousands of jobs a
minute rather than hundreds of thousands, yes, unreservedly. You lose a
moving part, you gain transactional enqueue, and your queue becomes
inspectable with the same SQL you already know. `SELECT count(*) FROM jobs
GROUP BY status` is a genuinely nice thing to be able to type during an
incident.

If you're doing enormous volume, or your jobs are sub-millisecond, the
per-claim write amplification will find you eventually. Measure before you
commit.

I'm not evangelising "just use Postgres" for everything. But I do think a
lot of us reach for a queue broker out of habit, and pay for it in
consistency bugs we then spend years working around.
