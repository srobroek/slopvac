## Summary

Replace the fixed one-second retry delay with a bounded exponential backoff strategy:

- Base delay: 200 ms
- Maximum delay: 30 seconds
- Maximum attempts: six
- Jitter added to avoid synchronized retries

The HTTP client now also honors `Retry-After` responses. In addition, this change fixes a bug that counted HTTP `429 Too Many Requests` responses as successful requests.

## Why

The fixed delay caused clients to retry at the same cadence, increasing the risk of repeated contention during rate limiting or service degradation. Exponential backoff with jitter spreads retry traffic over time, while `Retry-After` support respects server-provided rate-limit guidance.

Treating a `429` response as successful also produced incorrect request metrics and could hide failed operations.

## Testing

Adds four tests covering:

- Exponential delay growth from the 200 ms base
- Enforcement of the 30-second delay cap
- `Retry-After` handling
- Correct classification of `429` responses as failures

## Scope

- Three files changed
- Four tests added
