# Rate limit error

## Response

```
HTTP/1.1 429 Too Many Requests
Content-Type: application/json
Retry-After: 23
```

```json
{
  "error": {
    "code": "rate_limit_exceeded",
    "message": "Rate limit exceeded: 100 requests per minute per account. This request was not processed. Retry after 23 seconds; the Retry-After header carries the exact wait.",
    "limit": 100,
    "window_seconds": 60,
    "retry_after_seconds": 23,
    "account_id": "acct_31ab"
  }
}
```

## What happened

The request was rejected and not processed. No side effect occurred.

## Why

Your account sent more than 100 requests in the preceding 60 seconds. The limit is 100 requests per minute per account, counted over a rolling 60-second window rather than a fixed clock minute. The window advances continuously, so capacity returns as your oldest requests age past 60 seconds.

The limit applies to the account, not to the API key. Every key on the account draws from the same 100.

## What to do

1. Read `Retry-After`. It is an integer number of seconds until enough capacity frees for one request. Sleep that long, then retry the same request.
2. Retry with exponential backoff and jitter when the retry also returns 429. A fixed-interval retry from several clients converges on the same instant and hits the limit again.
3. Serialize your own concurrency. More than 100 in-flight requests per minute across your workers will hit this limit regardless of backoff.

```python
import time

import requests

def call(session, url, max_attempts=5):
    for attempt in range(max_attempts):
        response = session.get(url)
        if response.status_code != 429:
            return response
        time.sleep(int(response.headers.get("Retry-After", 1)))
    raise RuntimeError(f"still rate limited after {max_attempts} attempts")
```

Do not retry immediately without sleeping. A retry inside the window is rejected and still counts against the window.

## Checking your remaining capacity

Every response carries the current window state:

| Header | Meaning |
| --- | --- |
| `X-RateLimit-Limit` | `100` |
| `X-RateLimit-Remaining` | Requests available right now |
| `X-RateLimit-Reset` | Unix seconds at which the window has fully drained |

Read `X-RateLimit-Remaining` on 2xx responses and slow down before you reach zero.

## Raising the limit

Email support@example.com with your account ID, your sustained request rate, and your peak rate. Include the endpoints you call most.
