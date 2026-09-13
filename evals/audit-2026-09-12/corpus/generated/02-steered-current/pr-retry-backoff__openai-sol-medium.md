## What changed

- Replaced the fixed one-second retry delay with exponential backoff and jitter.
- Set the backoff base to 200 ms, the cap to 30 seconds, and the limit to six attempts.
- Made the HTTP client honour the `Retry-After` response header.
- Prevented HTTP 429 responses from being counted as successful requests.

## Why

Exponential backoff limits request frequency during repeated failures. Jitter reduces simultaneous retries from multiple clients.

Honouring `Retry-After` lets the server specify the retry delay. Treating HTTP 429 as unsuccessful keeps request results and retry behavior consistent.

## Test plan

- Run the four added tests.
- Verify that retry delays use a 200 ms base, exponential growth, jitter, and a 30-second cap.
- Verify that retries stop after six attempts.
- Verify that the HTTP client honours `Retry-After`.
- Verify that an HTTP 429 response does not count as success.
