# Improve HTTP retry behavior with exponential backoff and Retry-After support

## Overview

This PR improves the reliability and efficiency of HTTP request retries by implementing exponential backoff with jitter, adding support for the `Retry-After` header, and fixing a bug where 429 (Too Many Requests) responses were incorrectly treated as successful.

## Changes

### Retry Strategy
- **Replaced**: Fixed one-second retry interval
- **With**: Exponential backoff with jitter (base 200 ms, cap 30 s, six attempts)
- **Behavior**: Reduces server load during rate limiting while maintaining reasonable timeout bounds

### Retry-After Header Support
- HTTP client now respects the `Retry-After` header when present in responses
- Falls back to exponential backoff if header is absent or invalid
- Complies with RFC 7231 retry semantics

### Bug Fix
- Fixed bug where 429 (Too Many Requests) responses were counted as successful requests
- These responses now correctly trigger retry logic instead of being treated as terminal success

## Files Modified
- `http_client.py` — Core retry logic implementation
- `retry_strategy.py` — Exponential backoff algorithm with jitter calculation
- `exceptions.py` — Enhanced error handling for rate-limit scenarios

## Tests Added
- Test exponential backoff calculation and jitter distribution
- Test `Retry-After` header parsing and application
- Test 429 response triggers retry (not success)
- Test retry exhaustion after six attempts

## Impact
- **Resilience**: Better handling of rate-limited and temporarily unavailable services
- **Efficiency**: Reduced unnecessary server requests through strategic backoff
- **Compliance**: Honors server-provided retry guidance via `Retry-After`
- **Correctness**: Fixes regression where transient rate limits were masked as success
