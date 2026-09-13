## Replace fixed retry with exponential backoff and jitter; honor Retry-After header

### What changed

The HTTP client retry policy replaces a fixed one-second delay with exponential backoff. The backoff starts at 200 ms and increases by a factor of 2 per attempt, with random jitter between 0 and 100 ms added to each delay. Retries stop after six attempts or when the delay would exceed 30 seconds.

The HTTP client now reads the `Retry-After` response header and uses the server-specified delay when present, instead of ignoring it.

A bug fix corrects incorrect handling of 429 (Too Many Requests) responses. These responses were counted as successful, preventing retry. The client now retries on 429 responses.

### Why

Exponential backoff with jitter is standard for rate-limited APIs. It spreads retry traffic across time, reducing load spikes on a struggling service. The cap at 30 seconds and limit of six attempts bound the backoff to a reasonable window.

Respecting `Retry-After` headers gives the server control over retry timing. Ignoring it wastes resources and may aggravate rate limiting.

The 429 bug prevented the retry logic from running when the server explicitly signaled that the client should retry.

### Test plan

Four tests cover the new behavior:

- Exponential backoff increases by a factor of 2 with each retry, bounded at 30 seconds.
- Jitter adds random delay between 0 and 100 ms.
- `Retry-After` headers override exponential backoff with the server-specified delay.
- 429 responses trigger retry instead of succeeding.
