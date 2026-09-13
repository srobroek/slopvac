# gatekeep

`gatekeep` provides per-key token-bucket rate limiting with in-memory and Redis stores for Go applications.

## Usage

Create a `Limiter` with a refill rate, burst capacity, bucket lifetime, and store.

Use a stable key for each independent limit, such as an account ID, API token, or client address.

### Check without waiting

Call `Allow(key)` when the caller must receive an immediate decision.

```go
if !limiter.Allow(key) {
	// Reject the operation.
}
```

Each key uses a separate token bucket.

### Wait for capacity

Call `Wait(ctx, key)` when the operation can wait for a token.

```go
if err := limiter.Wait(ctx, key); err != nil {
	// The context was canceled or reached its deadline.
}
```

Set a context deadline to limit how long the caller can wait.

### Protect an HTTP handler

Use the `net/http` middleware to apply a limiter before requests reach a handler.

Choose a request-derived key that matches the required quota boundary.

For example, use an account ID for account quotas or a client address for network quotas.

## Stores

### In-memory store

Use the in-memory store when one Go process owns each bucket.

Buckets in separate processes do not share state.

### Redis store

Use the Redis store when multiple Go processes must share bucket state.

All processes enforcing one limit must use the same Redis deployment and key scheme.

## Configuration

| Name | Type | Default | Effect |
| --- | --- | --- | --- |
| `Rate` | Rate value | Set by the caller | Sets the token refill rate for each key. |
| `Burst` | Integer | Set by the caller | Sets the maximum number of tokens available in one bucket. |
| `TTL` | Duration | Set by the caller | Sets how long the store retains an inactive bucket. |

A request consumes one token from the bucket associated with its key.

The limiter rejects or delays the request when that bucket contains no tokens.
