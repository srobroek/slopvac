## What changed

The HTTP client now retries with exponential backoff and full jitter instead of a fixed one-second sleep.

- The delay for attempt *n* is `random(0, min(30s, 200ms * 2^(n-1)))`, so the five waits across six attempts sum to at most 6.2 s.
- The 30 s cap bounds both the computed delay and a server-supplied `Retry-After`. At the six-attempt limit the computed delay peaks at 6.4 s before jitter, so only `Retry-After` reaches the cap.
- The client parses `Retry-After` in both the delay-seconds and HTTP-date forms. A valid header replaces the computed delay for that attempt. An unparseable header falls back to the computed delay.
- A 429 response is now retryable. The previous branch treated any status below 500 as terminal success, so the client returned the 429 body and status to the caller on the first attempt and never retried.
- Exhausting six attempts raises `RetryExhausted` carrying the last response status.

## Why

The fixed one-second retry sent all clients back at the same instant, and the 429 misclassification surfaced rate-limit bodies to callers as if they were payloads.

## Test plan

Four tests in `tests/test_http_retry.py`:

- `test_backoff_schedule_bounds` injects a seeded RNG and asserts each of the five delays falls in `[0, min(30, 0.2 * 2**(n-1)))`.
- `test_retry_after_overrides_backoff` returns `Retry-After: 5` and asserts that the client sleeps 5 s rather than the computed delay.
- `test_429_is_retried` returns 429 twice then 200, and asserts three requests and a 200 result.
- `test_exhaustion_raises` returns 503 on every call, and asserts six requests and a `RetryExhausted` with status 503.

Run:

```
pytest tests/test_http_retry.py -q
```

The suite stubs the sleep function, so the four tests complete without real delay.
