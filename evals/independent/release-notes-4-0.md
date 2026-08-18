# objstore 4.0

We've been sitting on this one for a while. objstore 4.0 is the first release
since 3.0 that we're comfortable calling a rewrite of anything, and this time
two things got rewritten: how the client decides to try again, and how it moves
large objects onto the wire.

If you only read one paragraph: retries are now budget-based instead of
per-request, multipart uploads no longer require a seekable body, Node 16 is
gone, and every `*_config` name changed. The upgrade for most apps is a rename
pass and a version bump.

## The retry layer

The old retry code was a decorator on a single call. It counted attempts, it
slept for a bit, and it had no idea what else was happening in your process.
That worked fine right up until it didn't — the classic failure being a
partially-degraded bucket where 500 concurrent operations each independently
decide to retry three times, and your client turns a small server hiccup into a
2,000-request stampede.

4.0 replaces that with a retry budget shared across a client instance. Every
client keeps a token pool. A retry costs a token; a success returns a fraction
of one. When the pool empties, retries stop and errors surface immediately
instead of queueing behind a backoff timer. Under a sustained outage the client
converges on roughly one retry per ten successful requests rather than trying
forever.

The other change is that we finally distinguish between the two kinds of
failure that were previously the same thing. Timeouts, connection resets, and
503s are transient and retried. A 403, a checksum mismatch, or a malformed
request is terminal and is not — the old code would happily retry a signature
failure four times before giving up, which mostly served to make bad
credentials look like a network problem.

Backoff is decorrelated jitter now, capped at 20 seconds by default. If you had
hand-written your own backoff function to work around the old fixed
exponential, you can probably delete it.

## Streaming multipart uploads

`upload()` used to buffer. If you handed it a 4 GB file, it read the whole
thing to determine the part boundaries, and if you handed it a stream of
unknown length it refused outright. Plenty of people worked around this by
writing to a temp file first, which is a silly thing to make anyone do.

Multipart upload is now genuinely streaming. You pass any async iterable and
the client fills a bounded ring of part buffers, uploading them concurrently as
they fill. Peak memory is `part_size × concurrency`, which is 40 MB with the
defaults, whatever the size of the object. Unknown-length streams work. So do
pipes, sockets, and generators that produce data slowly.

Retries interact correctly with this: a failed part is re-uploaded from its own
retained buffer, and the buffer is released once the part is acknowledged. A
part that fails after its buffer is released is a hard error, which is why the
ring exists rather than a plain queue.

## Breaking changes

- **Node 16 is no longer supported.** It went end-of-life in September 2023.
  The minimum is now Node 20. We use `ReadableStream.from` and
  `AbortSignal.any` in the new upload path and are not polyfilling either.
- **All configuration options are renamed.** The `*_config` suffix is gone;
  options are grouped by concern. `retry_config` → `retry`, `http_config` →
  `transport`, `s3_config` → `endpoint`. The full mapping is in the migration
  guide.
- **`max_retries` is removed.** It has no meaning under a budget. Use
  `retry.budget` (token count) and `retry.max_attempts_per_request` if you need
  a hard per-call ceiling.
- **`upload()` no longer accepts a `content_length` hint.** It is computed or
  not needed.
- **Errors are a class hierarchy.** `ObjStoreError` is now a base class with
  `TransientError` and `TerminalError` subclasses. Code matching on
  `err.code === 'RETRY_EXHAUSTED'` needs updating; the string codes are gone.
- **`client.close()` is required** if you use the shared connection pool.
  Previously it was a no-op.

## Upgrading

```
npm install objstore@4
npx objstore-codemod v3-to-v4 src/
```

The codemod handles the config renames and the `max_retries` removal, and flags
error-code comparisons it can't rewrite for you. It does not touch your upload
call sites — those are almost always source-compatible, but read the diff
anyway.

Two things to check by hand:

1. If you construct clients per-request, you now want one long-lived client per
   process. The retry budget is per-instance, so a fresh client per request
   gives every request a full budget and defeats the mechanism entirely.
2. If you were relying on `upload()` buffering to hold a stream open, that
   behaviour is gone.

3.x moves to security-fix-only support for twelve months, through July 2027.

Thanks to the 41 people who filed issues against the 4.0 betas, and
particularly to the three of you who found the ring-buffer release bug before
we shipped it.
