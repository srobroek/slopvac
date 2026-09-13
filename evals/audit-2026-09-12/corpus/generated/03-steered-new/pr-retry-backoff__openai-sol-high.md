## What changed

- Replaced the fixed one-second retry delay with exponential backoff and jitter.
- Configured a 200 ms base delay, a 30-second delay cap, and six total attempts.
- Made the HTTP client honor the `Retry-After` response header.
- Fixed the success check so that HTTP 429 responses remain failures.

## Why

The fixed delay synchronized retrying clients during throttling events. Exponential backoff and jitter distribute retries while limiting delays to 30 seconds.

Servers use `Retry-After` to specify when clients should retry. Treating HTTP 429 as success bypassed the retry behavior.

## Test plan

- Verify exponential backoff and jitter from the 200 ms base delay.
- Verify that retry delays do not exceed 30 seconds.
- Verify that the client honors `Retry-After`.
- Verify that HTTP 429 does not count as success.

The change added four tests covering these cases.
