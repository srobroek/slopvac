# gatekeep

`gatekeep` provides per-key token-bucket rate limiting for Go applications, with memory, Redis, and `net/http` integrations.

## Usage

Create a `Limiter` with a refill rate, burst capacity, bucket lifetime, and store.

Call `Allow(key)` when the caller needs an immediate rate-limit decision.

Call `Wait(ctx, key)` when the caller can wait for a token. The wait ends when the context ends.

Use a stable key for each independently limited resource, such as an account ID, API token, or IP address.

```go
if limiter.Allow(key) {
	// Process the operation.
}
```

```go
if err := limiter.Wait(ctx, key); err != nil {
	return err
}

// Process the operation.
```

## Stores

### In-memory store

The in-memory store keeps buckets inside one Go process. Separate processes do not share its bucket state.

Use this store when one process handles all requests for each key.

### Redis store

The Redis store keeps per-key bucket state in Redis. Application processes that use the same Redis instance share that state.

Use this store when multiple processes must enforce one limit for the same key.

## HTTP middleware

The `net/http` middleware applies a limiter before it calls the wrapped handler.

Configure the middleware with the key that identifies each independently limited client or resource.

## Configuration

| Name | Type | Default | Effect |
| --- | --- | --- | --- |
| `Rate` | Rate value | Zero value | Sets the number of tokens added to each bucket over time. |
| `Burst` | Integer | `0` | Sets the maximum number of tokens that each bucket can hold. |
| `TTL` | Duration | `0` | Sets how long the store retains each per-key bucket. |

Each key receives an independent bucket configured with the same `Rate`, `Burst`, and `TTL` values.
