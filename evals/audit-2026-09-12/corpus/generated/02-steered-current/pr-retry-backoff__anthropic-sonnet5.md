## What changed

- Replace the fixed 1-second retry delay with exponential backoff and jitter: base 200 ms, cap 30 s, 6 attempts.
- Make the HTTP client honor the `Retry-After` header when present, using it in place of the computed backoff delay.
- Fix a bug where a 429 response was counted as a success, so callers now see it as a retryable failure.

Files touched: 3. Tests added: 4, covering backoff timing, the `Retry-After` override, the 429 fix, and exhaustion after 6 attempts.

## Why

The fixed 1-second delay retried too fast under sustained load and ignored server-provided `Retry-After` guidance. The 429-as-success bug suppressed retries on rate-limited requests, causing silent data loss.

## Test plan

- Added 4 unit tests:
  - Backoff delay sequence matches base 200 ms, cap 30 s, across 6 attempts.
  - `Retry-After` header value overrides the computed backoff delay.
  - A 429 response is treated as a failure and triggers a retry.
  - All 6 attempts exhausted returns the final error to the caller.
- Ran the existing retry and HTTP client test suites; all pass.
