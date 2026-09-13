## What changed

- Replaced the fixed one-second retry delay with exponential backoff and jitter.
- Set the backoff base to 200 ms, the cap to 30 seconds, and the limit to six attempts.
- Made the HTTP client honor the `Retry-After` response header.
- Fixed response handling so that HTTP 429 no longer counts as success.
- Added four automated tests across the three changed files.

## Why

The fixed delay retried throttled requests at a constant rate and ignored server-provided timing. Counting HTTP 429 as success also bypassed failure handling.

## Test plan

Run the four added tests before merge:

- Verify that retries use a 200 ms base with exponential backoff and jitter.
- Verify that retry delays do not exceed 30 seconds across six attempts.
- Verify that the client honors `Retry-After`.
- Verify that HTTP 429 does not count as success.
