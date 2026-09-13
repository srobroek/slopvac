## What changed

- Replaced the fixed one-second retry delay with exponential backoff.
- Added jitter with a 200 ms base delay and a 30-second maximum delay.
- Limited each request to six attempts.
- Updated the HTTP client to honor the server’s `Retry-After` value.
- Fixed response accounting so HTTP 429 responses count as failures instead of successes.
- Updated three files and added four tests.

## Why

Exponential backoff with jitter reduces synchronized retry bursts during transient failures. Honoring `Retry-After` lets the server specify when rate-limited requests should retry. Counting HTTP 429 responses as failures keeps retry and success metrics accurate.

## Test plan

- Added four tests covering the retry schedule, six-attempt limit, `Retry-After` handling, and HTTP 429 accounting.
- Verified that the retry schedule uses a 200 ms base, jitter, and a 30-second cap.
- Run the project test suite and verify that all existing and new tests pass.
