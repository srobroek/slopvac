# Rate limit error

## Response

```http
HTTP/1.1 429 Too Many Requests
Content-Type: application/json
Retry-After: 23
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1770000023

{
  "error": {
    "code": "rate_limit_exceeded",
    "message": "Rate limit exceeded: 100 requests per minute per account. Your account sent 100 requests in the last 60 seconds. Wait 23 seconds, then retry. Read the Retry-After header for the exact wait in seconds.",
    "limit": 100,
    "window_seconds": 60,
    "retry_after_seconds": 23,
    "account_id": "acct_8Q2vK1"
  }
}
```

## What happened

Your account sent more than 100 requests in the last 60 seconds. The service rejected this request and ran none of it. Nothing was created, changed, or charged.

The limit counts requests per account, not per API key. Every key on `acct_8Q2vK1` shares the same 100.

## Why 23 seconds

The window rolls. The counter is the number of requests in the trailing 60 seconds, not a count that resets on the minute. `Retry-After` is the seconds until the oldest of those 100 requests leaves the window, which frees one slot.

## What to do

1. Sleep for the number of seconds in the `Retry-After` header, then send the request again. Do not compute your own delay; `Retry-After` is exact for this account at this moment.
2. Retry with exponential backoff and jitter if the retry also returns 429. A fixed delay from many workers refills the window at the same instant.
3. Read `X-RateLimit-Remaining` on every 2xx response and slow down before you reach 0.
4. Send one request at a time per account for a batch job, or cap concurrency so your workers together stay under 100 per minute.

```python
resp = client.post(url, json=body)
if resp.status_code == 429:
    time.sleep(int(resp.headers["Retry-After"]))
    resp = client.post(url, json=body)
```

A request that returns 429 does not count against the limit.

To raise the limit for `acct_8Q2vK1`, open a request at https://dashboard.example.com/support with your peak requests per minute.
