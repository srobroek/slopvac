## What changed

- Replaced the fixed one-second retry delay with exponential backoff and jitter.
- Set the backoff base to 200 ms, the cap to 30 seconds, and the limit to six attempts.
- Made the HTTP client honour the server-provided `Retry-After` delay.
- Prevented HTTP 429 responses from counting as successful requests.
- Changed three files and added four tests.

## Why

The client must apply bounded retry delays, respect server throttling instructions, and report HTTP 429 responses as failures.

## Test plan

- Verify that retry delays use a 200 ms base and exponential growth.
- Verify that retry delays never exceed the 30-second cap.
- Verify that the client honours `Retry-After` and stops after six attempts.
- Verify that an HTTP 429 response does not count as success.
