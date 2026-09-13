# fix(http): exponential backoff with jitter, honour `Retry-After`, stop treating 429 as success

## What changed

- The retry budget is six attempts: one initial request plus five retries. It was six attempts before this change as well.
- The delay before retry `n` (zero-indexed) is now `random(0, min(30s, 200ms * 2^n))`. It was a fixed 1 s sleep.
- The computed ceilings are 200 ms, 400 ms, 800 ms, 1600 ms, and 3200 ms. Worst-case total sleep is 6.2 s, and expected total sleep is 3.1 s against 5 s before.
- The client reads `Retry-After` on 429 and 503 responses. It accepts both the delay-seconds and the HTTP-date form, clamps the result to the 30 s cap, and sleeps that instead of the computed delay.
- If `Retry-After` is absent or unparseable, the client falls back to the computed delay.
- A 429 response no longer counts as success. The client retries it, and returns a `*RetryError` once the sixth attempt fails.

## Why

The 429 bug returned the throttle body to callers as if it were payload, so a rate-limited fetch decoded an empty result set and reported no error. Fixed 1 s retries also put every client in the fleet back on the wire in the same 1 s slot after a shared outage, which the jitter term breaks up.

## Compatibility

Callers that branch on `status == 200` see no change. A caller that read the body of a 429 now receives an error after the retry budget is spent, and the response body is discarded.

## Test plan

Four tests added:

- `TestBackoffScheduleWithinBounds` asserts each of the five delays falls in `[0, min(30s, 200ms*2^n)]` with a seeded random source.
- `TestRetryAfterOverridesBackoff` asserts a `Retry-After: 5` header produces a 5 s sleep on a 429.
- `TestRetryAfterClampedToCap` asserts a `Retry-After: 120` header produces a 30 s sleep.
- `TestTooManyRequestsIsNotSuccess` asserts six 429 responses produce a `*RetryError` and six recorded requests.

Run:

```
go test ./internal/httpclient/ -race -count 1
```

The suite uses a fake clock, so the four tests add 0.4 s to the package runtime.
