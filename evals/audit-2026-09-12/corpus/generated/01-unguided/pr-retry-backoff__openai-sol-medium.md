## Summary

This change improves retry behavior for rate-limited and transient HTTP responses.

- Replaces the fixed one-second delay with exponential backoff and jitter
- Uses a 200 ms base delay, capped at 30 seconds
- Limits requests to six attempts
- Honors server-provided `Retry-After` values
- Fixes a bug that counted `429 Too Many Requests` responses as successful

## Why

A fixed retry interval can synchronize clients and increase pressure on an already constrained service. Exponential backoff with jitter spreads retries over time, while `Retry-After` support allows the server to control when the next request should occur.

The `429` classification bug also caused failed, rate-limited requests to be reported as successful.

## Test coverage

Adds four tests covering:

- Exponential delay growth
- Jitter and the 30-second cap
- `Retry-After` handling
- `429` responses being treated as failures rather than successes

## Scope

- Three files changed
- Four tests added
