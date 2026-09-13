## What changed

- Replaced the fixed one-second retry delay across three files with exponential backoff.
- Configured retries with a 200 ms base delay, a 30-second cap, jitter, and six attempts.
- Updated the HTTP client to honor the `Retry-After` response header.
- Fixed 429 handling so rate-limit responses count as failures instead of successes.
- Added four tests covering backoff, attempt limits, `Retry-After`, and 429 handling.

## Why

A fixed one-second delay can synchronize retries and increase load during rate limiting. Exponential backoff with jitter spreads retry traffic across time. `Retry-After` lets the server provide the delay that the client should use. Treating 429 responses as failures gives callers the correct request outcome.

## Test plan

- [ ] Run the existing test suite.
- [ ] Verify the four new tests pass.
- [ ] Verify retries use exponential backoff with jitter.
- [ ] Verify retries stop after six attempts and delays do not exceed 30 seconds.
- [ ] Verify the client honors `Retry-After`.
- [ ] Verify a 429 response does not count as success.
