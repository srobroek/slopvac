# Replace fixed retry delay with exponential backoff and jitter

## What changed

- The retry loop computes each delay as `random(0, min(30s, 200ms × 2^attempt))` instead of sleeping a fixed 1 s. Six attempts give sleeps drawn below 200 ms, 400 ms, 800 ms, 1.6 s, and 3.2 s, so a fully exhausted retry sequence waits at most 6.2 s.
- The HTTP client reads `Retry-After` on 429 and 503 responses. It accepts delta-seconds and HTTP-date forms, and clamps the parsed value to the 30 s cap. When the header is absent or unparseable, the client falls back to the computed backoff delay.
- The retry classifier now treats 429 as retryable. Before this change it matched only 5xx status codes, so a 429 fell through to the success path and callers received the throttling body as a valid response.

## Why

The 30 s cap bounds a single wait when a server asks for a long `Retry-After`. Full jitter, rather than a fixed delay, spreads the retries of concurrent callers that a single upstream outage synchronizes.

## Test plan

Four tests were added:

- `test_backoff_schedule_bounds` asserts every generated delay falls in `[0, min(30s, 200ms × 2^attempt))` across all six attempts.
- `test_retry_after_seconds_overrides_backoff` returns `Retry-After: 5` on a 429 and asserts the client waits 5 s.
- `test_retry_after_clamped_to_cap` returns `Retry-After: 120` and asserts the client waits 30 s.
- `test_429_is_retried_not_returned` serves a 429 followed by a 200 and asserts the caller receives the 200 body.

Run the suite with `cargo test --package http-client retry`.
