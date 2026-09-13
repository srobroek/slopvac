## What changed

- Replace the fixed one-second retry delay with exponential backoff: base 200 ms, cap 30 s, six attempts total, with jitter applied to each delay.
- Make the HTTP client honor a `Retry-After` header when the server sends one, using it instead of the computed backoff delay.
- Fix a bug where the client counted a 429 response as success and stopped retrying.

Three files change; four tests cover the new backoff schedule, the `Retry-After` handling, and the 429 fix.

## Why

The fixed one-second delay retried too fast against rate limits and did not spread retries under load. The 429-as-success bug caused the client to return a rate-limited response to the caller without retrying.

## Test plan

- Added a test asserting the delay sequence for six attempts falls within the jittered bounds of the 200 ms base and 30 s cap.
- Added a test asserting the client waits for the duration in `Retry-After` when present.
- Added a test asserting a 429 response triggers a retry instead of returning success.
- Added a test asserting the client stops after six attempts and surfaces the last error.
