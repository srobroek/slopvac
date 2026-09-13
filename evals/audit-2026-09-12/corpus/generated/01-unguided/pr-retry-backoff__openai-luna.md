## Summary

Replaces the fixed one-second retry delay with bounded exponential backoff and jitter, and improves handling of rate-limited HTTP requests.

## Changes

- Retry delays now use exponential backoff with:
  - 200 ms base delay
  - 30-second maximum delay
  - Six total attempts
  - Jitter to reduce synchronized retry spikes
- The HTTP client now honors the `Retry-After` response header when present.
- Fixed a bug where HTTP `429 Too Many Requests` responses were incorrectly counted as successful requests.
- Added four tests covering retry timing, attempt limits, `Retry-After`, and 429 success accounting.

## Reviewer focus

- Verify that `Retry-After` takes precedence over the calculated backoff where appropriate.
- Confirm that the six-attempt limit includes the initial request.
- Check that jitter remains bounded by the configured backoff cap.
- Confirm that 429 responses are recorded as failures and retried according to the expected policy.
