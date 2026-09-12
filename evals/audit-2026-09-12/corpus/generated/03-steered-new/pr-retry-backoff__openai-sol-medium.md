## What changed

- Replaced the fixed one-second retry delay with exponential backoff and jitter.
- Set the backoff base to 200 ms, the cap to 30 seconds, and the limit to six attempts.
- Made the HTTP client honor `Retry-After` responses.
- Counted HTTP 429 responses as failed attempts instead of successful requests.

## Why

The fixed delay retried throttled requests without using the server-provided retry interval. The success counter also produced incorrect results for HTTP 429 responses.

## Test plan

Added four tests covering:

1. Verify that retry delays increase from the 200 ms base.
2. Verify that retry delays do not exceed the 30-second cap.
3. Verify that `Retry-After` controls the retry delay.
4. Verify that an HTTP 429 response counts as a failed attempt.
