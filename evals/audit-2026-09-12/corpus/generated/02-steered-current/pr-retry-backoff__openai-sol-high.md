## What changed

- Replaced the fixed one-second retry delay with exponential backoff starting at 200 ms.
- Capped retry delays at 30 seconds and limited requests to six attempts.
- Added jitter to each exponential backoff delay.
- Made the HTTP client honor the server-provided `Retry-After` value.
- Classified HTTP 429 responses as retryable failures instead of successful responses.

## Why

The fixed delay ignored server timing guidance and sent retries at synchronized intervals. The 429 classification also allowed rate-limited requests to report success.

## Test plan

The change adds four tests:

- Verify exponential delays start at 200 ms and stop increasing at 30 seconds.
- Verify the client stops after six attempts.
- Verify the client honors `Retry-After`.
- Verify a 429 response does not count as success.
