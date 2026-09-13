# gatekeep

`gatekeep` is a token-bucket rate limiter for Go applications. It provides:

- Independent rate-limit buckets for each key
- In-memory storage for single-process applications
- Redis storage for distributed applications
- Blocking and non-blocking APIs
- `net/http` middleware
- Automatic cleanup of inactive buckets through configurable TTLs

## Installation

```sh
go get gatekeep
```

Replace `gatekeep` with the module path used by your project if necessary.

## How it works

Each key identifies a separate token bucket. A key can represent a user, API token, tenant, IP address, route, or another resource.

A bucket:

- Receives tokens at the configured `Rate`
- Holds at most `Burst` tokens
- Spends one token for each allowed operation
- Expires after the configured `TTL` when inactive

For example, a limiter with a rate of 10 and a burst of 20 permits a short burst of up to 20 operations, then replenishes capacity at 10 tokens per second.

## Configuration

Configure a limiter with `Limiter`:

```go
config := gatekeep.Limiter{
    Rate:  10,
    Burst: 20,
    TTL:   time.Hour,
}
```

| Field | Description |
| --- | --- |
| `Rate` | Rate at which tokens are added to each bucket. |
| `Burst` | Maximum number of tokens a bucket can hold. |
| `TTL` | How long an inactive bucket remains in the selected store. |

Choose a TTL long enough to preserve useful bucket state, but short enough to remove keys that are no longer active.

## Choosing a store

### In-memory store

Use the in-memory store when:

- The application runs as a single process
- Rate-limit state does not need to survive restarts
- Each application instance may enforce its own independent limit
- Low latency is more important than shared state

In a multi-instance deployment, every process has a separate in-memory bucket for the same key. Traffic distributed across instances can therefore exceed the intended aggregate limit.

### Redis store

Use the Redis store when:

- Several application instances must share limits
- Limits must apply consistently across a distributed deployment
- Bucket state should remain available when an application instance restarts

Redis adds network latency and an operational dependency, but provides a common source of rate-limit state.

## Checking without waiting

Use `Allow` when the caller should continue immediately or reject the operation:

```go
if !limiter.Allow(userID) {
    return errors.New("rate limit exceeded")
}

performOperation()
```

`Allow(key)` consumes a token when one is available and returns whether the operation may proceed.

Buckets are independent:

```go
limiter.Allow("user:alice")
limiter.Allow("user:bob")
```

Activity for `user:alice` does not consume capacity from `user:bob`.

## Waiting for capacity

Use `Wait` when the operation may pause until a token becomes available:

```go
if err := limiter.Wait(ctx, userID); err != nil {
    return err
}

performOperation()
```

Always pass a context with an appropriate deadline when waiting is bounded:

```go
ctx, cancel := context.WithTimeout(ctx, 500*time.Millisecond)
defer cancel()

if err := limiter.Wait(ctx, userID); err != nil {
    return fmt.Errorf("wait for rate limit: %w", err)
}
```

`Wait(ctx, key)` returns when a token is available or when the context is canceled or reaches its deadline.

Use `Allow` for request rejection and load shedding. Use `Wait` for background work, outbound API calls, and other operations where delaying is preferable to failing immediately.

## HTTP middleware

The `net/http` middleware applies the limiter before invoking the next handler. Select a stable key that matches the scope of the policy, such as an authenticated account or API token.

```go
mux := http.NewServeMux()
mux.HandleFunc("/api/items", itemsHandler)

// Construct the gatekeep middleware with the configured limiter and key
// function, then wrap mux before passing it to the server.
handler := rateLimitMiddleware(mux)

server := &http.Server{
    Addr:              ":8080",
    Handler:           handler,
    ReadHeaderTimeout: 5 * time.Second,
}

log.Fatal(server.ListenAndServe())
```

A key function commonly derives a key from request data:

```go
func keyForRequest(r *http.Request) string {
    if userID, ok := authenticatedUserID(r.Context()); ok {
        return "user:" + userID
    }

    return "ip:" + clientIP(r)
}
```

Prefer authenticated identifiers over IP addresses. Many users can share one public IP, and untrusted forwarding headers can allow clients to select arbitrary keys.

When limiting by client IP:

- Trust `X-Forwarded-For` or similar headers only behind a configured proxy
- Normalize addresses consistently
- Decide whether IPv6 addresses should be grouped by prefix
- Avoid including ephemeral client ports

## Key design

Keys define isolation between buckets. Keep them stable, bounded, and free of sensitive data.

Examples:

```text
user:12345
tenant:acme
token:7f91c2...
route:/v1/search:user:12345
```

Include every dimension required by the policy:

```go
key := "tenant:" + tenantID + ":route:search"
```

Avoid placing raw credentials, session tokens, email addresses, or other sensitive values in keys. Hash sensitive identifiers when they must participate in a key.

Unbounded attacker-controlled keys can create excessive store entries. Validate or normalize user-controlled values and configure a suitable `TTL`.

## Error handling

A non-blocking check has two outcomes:

```go
if limiter.Allow(key) {
    // Accepted.
} else {
    // Rate limited.
}
```

A blocking check can also stop because its context ended:

```go
err := limiter.Wait(ctx, key)
switch {
case err == nil:
    // Accepted.
case errors.Is(err, context.Canceled):
    // The caller canceled the operation.
case errors.Is(err, context.DeadlineExceeded):
    // Capacity was not available before the deadline.
default:
    // Handle a store or limiter error if supported by the configured backend.
}
```

For HTTP APIs, rejected requests commonly use status `429 Too Many Requests`. If the application can calculate an accurate retry delay, include a `Retry-After` header.

## Operational guidance

### Select a burst deliberately

A burst of 1 produces a smooth limit but gives little tolerance for normal request clustering. A larger burst absorbs short spikes while preserving the long-term rate.

### Set request deadlines

Do not call `Wait` indefinitely from latency-sensitive handlers. Derive its context from the request or use a shorter child deadline.

### Plan for Redis failures

Decide whether the application should fail open or fail closed when Redis is unavailable:

- **Fail open:** preserve availability, but temporarily permit excess traffic.
- **Fail closed:** preserve the limit, but reject traffic during store failures.

Apply the policy consistently and monitor store errors.

### Monitor rejected and delayed work

Useful metrics include:

- Allowed operations
- Rejected operations
- Time spent waiting
- Context cancellations and deadline expirations
- Redis latency and errors
- Number of active keys, when available

Avoid using raw rate-limit keys as metric labels because they can create unbounded metric cardinality.

## Testing

Give each test its own store or key so bucket state does not leak between cases.

Test at least:

- Requests within the initial burst
- Rejection after the bucket is exhausted
- Token replenishment over time
- Independence between keys
- Cancellation of `Wait`
- Bucket expiration after the TTL
- Shared behavior across instances when using Redis

Use short, bounded contexts in tests so failures do not hang the test suite:

```go
ctx, cancel := context.WithTimeout(context.Background(), time.Second)
defer cancel()

if err := limiter.Wait(ctx, "test-key"); err != nil {
    t.Fatal(err)
}
```
