## What changed

- Updated three files to replace the fixed one-second retry delay with exponential backoff.
- Set the backoff base to 200 ms.
- Capped the backoff delay at 30 seconds.
- Limited each request to six total attempts.
- Added jitter to retry delays.
- Updated the HTTP client to honor the `Retry-After` response header.
- Fixed 429 handling so rate-limited responses count as failures.
- Added four tests covering backoff, jitter, `Retry-After`, and 429 classification.

## Why

The fixed one-second delay synchronized retries from multiple failed requests. Exponential backoff with jitter spreads retry traffic across time.

The HTTP client must follow server-provided retry timing. A 429 response must report failure because the server rejected the request.

## Test plan

- [ ] Run the existing test suite.
- [ ] Verify the four new tests pass.
- [ ] Verify retries use a 200 ms base, a 30-second cap, and six total attempts.
- [ ] Verify the client honors `Retry-After`.
- [ ] Verify a 429 response reports failure.
