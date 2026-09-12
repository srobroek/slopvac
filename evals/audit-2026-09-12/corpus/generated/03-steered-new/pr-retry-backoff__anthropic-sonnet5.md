## What changed

- Replace the fixed one-second retry delay in the HTTP client with exponential backoff: base 200 ms, cap 30 s, six attempts.
- Add jitter to each backoff interval to avoid synchronized retries across clients.
- Honor the `Retry-After` header when present, using its value instead of the computed backoff for that attempt.
- Fix a bug where a 429 response was counted as success, so the client stopped retrying instead of backing off.

## Why

The fixed one-second delay retried too fast against a rate-limited backend and ignored `Retry-After`, and the 429-as-success bug meant callers received partial or empty results instead of a retried request.

## Test plan

- Added four tests:
  - Backoff delay sequence matches base 200 ms, cap 30 s, across six attempts.
  - `Retry-After` header value overrides the computed backoff for that attempt.
  - A 429 response triggers a retry instead of being treated as success.
  - Retry stops after six attempts and returns the last error.
- Ran the updated test suite for the three touched files; all pass.
