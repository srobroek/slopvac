## What changed

Replaced the fixed one-second retry delay with exponential backoff. The client now waits 200 ms on the first retry, doubling the delay after each failure. It caps the delay at 30 seconds across six attempts. This reduces load on a recovering service and prevents retry storms.

The HTTP client now reads and respects the `Retry-After` header when present, using its value instead of the calculated backoff delay. This honors the service's recovery timeline.

Fixed a bug where the client treated a 429 (Too Many Requests) response as a successful response. The client now retries on 429 and other retryable status codes, instead of returning them to the caller.

## Why

Exponential backoff with jitter prevents thundering herd problems when multiple clients retry at the same interval. The 200 ms base and 30 second cap balance quick recovery for transient failures against respectful backoff during extended outages.

`Retry-After` compliance lets services communicate their actual recovery window, improving efficiency for both client and server during degradation.

The 429 bug caused callers to treat rate limits as successful responses, masking the condition and preventing proper error handling.

## Test plan

Added four tests covering exponential backoff calculations, `Retry-After` header parsing, retry exhaustion, and correct status code classification. All tests pass. Verified existing tests remain green.
