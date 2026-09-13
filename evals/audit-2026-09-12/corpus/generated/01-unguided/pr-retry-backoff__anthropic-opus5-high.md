# Replace fixed retry delay with exponential backoff and jitter; honour `Retry-After`; stop counting 429 as success

## Why

Three problems in the retry path, in increasing order of severity:

1. **Fixed one-second delay.** Every retry slept exactly 1000 ms. When an upstream dependency degraded, all in-flight callers retried in lockstep, which turned a partial outage into a synchronised load spike against the recovering service.
2. **`Retry-After` was ignored.** The server told us when to come back and we retried on our own schedule anyway, which extended throttling windows that would otherwise have cleared.
3. **429 was classified as success.** The status check treated any response that was not a 5xx or a transport error as a successful call. A throttled request therefore returned a 429 body to the caller as if it were a valid payload, and the retry loop never engaged. This is the actual bug behind the intermittent parse failures downstream: callers were deserialising a rate-limit error document.

Item 3 is a correctness fix and is the reason this is not a pure tuning change.

## What changed

**Retry policy (new backoff computation).** The delay for retry `n` (zero-indexed) is now `random(0, min(cap, base * 2^n))` with `base = 200 ms` and `cap = 30 s`: full jitter, not equal jitter, so a cluster of clients spreads across the whole window rather than clumping at the midpoint. The attempt budget is six, meaning one initial call plus five retries.

Resulting schedule, with the maximum sleep per retry:

| Retry | Uncapped `base * 2^n` | Sleep drawn from |
| ----- | --------------------- | ---------------- |
| 1 | 200 ms | 0 – 200 ms |
| 2 | 400 ms | 0 – 400 ms |
| 3 | 800 ms | 0 – 800 ms |
| 4 | 1.6 s | 0 – 1.6 s |
| 5 | 3.2 s | 0 – 3.2 s |

Worst-case added latency from sleeping is 6.2 s, against 5 s before, so the p100 tail moves only slightly. The 30 s cap is not reached at six attempts; it exists to bound the schedule if the attempt count is raised later and to clamp `Retry-After`, described below. I kept the cap rather than dropping it as dead configuration because the clamp path does use it.

**HTTP client honours `Retry-After`.** Both header forms are parsed: `delta-seconds` and the HTTP-date form. A server-supplied delay takes precedence over the computed backoff, is clamped to the 30 s cap, and negative or past-dated values collapse to zero. An unparseable header falls back to the computed backoff instead of failing the request, so a malformed header from an upstream cannot break the call. Jitter is not added on top of a server-specified delay; the server named a time and adding spread would only push us past it.

**429 is a retryable failure.** The success predicate now keys on the 2xx range rather than "not 5xx". 429 and 503 both enter the retry path, and after the attempt budget is exhausted the caller receives a rate-limit error rather than a 429 body dressed up as a result.

Three files touched: the retry policy that computes delays, the HTTP client that consumes the policy and reads the header, and the response classification used by the client.

## Tests

Four new tests:

1. Backoff sequence is bounded correctly: for each retry index, the drawn delay sits in `[0, min(cap, base * 2^n)]`, and the sequence is exhausted after six attempts.
2. Jitter actually varies: repeated draws at the same retry index are not all identical, and stay inside the bound.
3. `Retry-After` overrides the computed delay, for both `delta-seconds` and HTTP-date, including the clamp at 30 s and the fallback when the header is garbage.
4. A 429 is retried and, once the budget is spent, surfaces as an error. This test fails on the parent commit, which is the regression guard for the classification bug.

The clock and the jitter source are injected in these tests, so no test sleeps in real time and the assertions are deterministic where determinism is meaningful.

## Review notes

- **Where to look first:** the success predicate. If the 2xx boundary is wrong for any status this client sees in practice (204, 3xx from a redirect-following transport), that is the change most likely to have a blind spot.
- **Retry-After precedence** is a judgement call. I let the server win unconditionally, subject to the cap. If you would rather take `max(server, computed)` so we never retry sooner than our own schedule allows, say so; it is a one-line change.
- **Non-idempotent requests** are out of scope here. This change does not alter which requests are eligible for retry, only the timing and the 429 classification. If any caller sends non-idempotent writes through this client, the extra retries from fixing 429 will now fire where they previously did not, and that deserves its own look.
- The attempt count, base, and cap are the existing configuration knobs; defaults changed, the surface did not.

## Risk

Callers that were inspecting the returned 429 body themselves, if any exist, will now see an error instead. I did not find such a caller. Retry volume against a throttling upstream will rise, since 429 now retries where it previously did not; the jitter and the escalating delays are what keep that from becoming a hot loop.
