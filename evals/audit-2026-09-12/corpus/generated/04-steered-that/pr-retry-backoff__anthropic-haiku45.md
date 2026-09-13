## What changed

The retry mechanism now uses exponential backoff with jitter instead of a fixed one-second delay. Each attempt waits base 200 ms, with backoff doubling until it caps at 30 seconds, across six total attempts.

The HTTP client honours the `Retry-After` header when a server provides it, deferring to the server's specified retry delay over the backoff schedule.

The client now treats HTTP 429 responses as failures. Previously, a 429 (Too Many Requests) response incremented the success counter instead of the retry counter, causing the client to report success when rate-limited.

## Why

Exponential backoff with jitter reduces cascading failures when a service experiences issues. Fixed one-second delays force all clients to retry at the same moment, amplifying load on a recovering server. Jitter spreads retry attempts across time, allowing the server to handle requests incrementally.

Honouring `Retry-After` complies with HTTP 1.1 specification and respects explicit server guidance on retry timing. The server's signal takes precedence when available.

Counting 429 as success hid rate-limit failures from callers, breaking error handling that depends on accurate status. The fix ensures that rate-limiting is visible in the retry logic and to the caller.

## Test plan

Four new tests verify retry behaviour: one confirms exponential timing (base 200 ms, cap 30 seconds, six attempts), one verifies `Retry-After` header delays override backoff, one confirms 429 responses trigger retries instead of success, and one confirms the client respects the six-attempt limit.

Run `make test` to execute the full suite.
