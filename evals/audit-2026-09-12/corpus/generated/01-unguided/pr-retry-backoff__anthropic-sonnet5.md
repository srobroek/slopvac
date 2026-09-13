# Improve HTTP retry behavior: backoff, jitter, and 429 handling

## Summary

Replaces the fixed one-second retry delay with exponential backoff plus jitter, adds support for the `Retry-After` header, and fixes a bug where a `429` response was incorrectly treated as a successful request.

## Changes

- **Backoff strategy**: retry delay is now computed as exponential backoff with a 200 ms base and a 30 s cap, jittered to avoid thundering-herd retries against the same endpoint. Attempts are capped at six.
- **`Retry-After` support**: when a response includes a `Retry-After` header, the client now waits for the server-specified duration instead of applying the computed backoff delay.
- **429 bug fix**: the retry loop previously classified `429 Too Many Requests` as a successful response, so callers received a "success" result carrying no usable data. `429` is now treated as retryable, consistent with `5xx` responses.

## Files touched

- 3 source files (retry loop, backoff calculation, HTTP client response handling)

## Testing

Added four tests covering:

1. Backoff delay growth stays within the 200 ms base / 30 s cap bounds across six attempts.
2. Jitter produces varying delays rather than deterministic ones on repeated calls.
3. `Retry-After` header value takes precedence over the computed backoff delay.
4. A `429` response is now classified as retryable rather than success.

## Reviewer notes

- Please double-check the six-attempt limit matches expectations for downstream timeout budgets — total worst-case wait time is now bounded by the 30 s cap per attempt rather than growing unbounded.
- Worth confirming no other call sites depended on the previous (buggy) behavior of treating `429` as success.
