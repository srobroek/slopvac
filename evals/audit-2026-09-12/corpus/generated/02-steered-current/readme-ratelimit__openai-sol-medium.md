# gatekeep

`gatekeep` provides per-key token-bucket rate limiting through in-memory and Redis stores, with middleware for `net/http`.

## Install

Add the module path from `gatekeep`'s `go.mod` file to your application:

```sh
go get <module-path>
```

Import the package using the same module path:

```go
import "<module-path>"
```

## Usage

Create a `Limiter` with a token rate, burst capacity, and inactive-bucket lifetime. Select the in-memory store for one process or the Redis store for shared limits.

Call `Allow(key)` when the caller can handle an immediate decision:

```go
if !limiter.Allow("customer:123") {
	// Reject or defer the operation.
}
```

Call `Wait(ctx, key)` when the operation can wait for a token:

```go
if err := limiter.Wait(ctx, "customer:123"); err != nil {
	// The context expired or was canceled.
}
```

Use a stable key for each rate-limited identity. Examples include a customer ID, API token, account ID, or IP address.

## Stores

### In-memory store

The in-memory store keeps buckets inside one Go process. Separate processes enforce separate limits when each process uses its own store.

### Redis store

The Redis store keeps bucket state in Redis. Applications that use the same Redis store and key namespace share rate limits.

## HTTP middleware

Wrap a `net/http` handler with the package middleware. The middleware derives a key for each request and applies the configured `Limiter`.

Choose a key that represents the protected identity. A client-supplied header requires authentication before the middleware can trust its value.

## Configuration

| Name | Type | Default | Effect |
| --- | --- | --- | --- |
| `Rate` | Rate value | Package-defined | Sets the number of tokens replenished per time interval. |
| `Burst` | Integer | Package-defined | Sets the maximum number of tokens available in one bucket. |
| `TTL` | Duration | Package-defined | Removes bucket state after the configured inactive period. |

Each key receives an independent token bucket. A request consumes one token from the bucket associated with its key.

`Allow(key)` returns immediately. It permits the operation when the bucket contains a token and rejects the operation when no token remains.

`Wait(ctx, key)` waits until the bucket provides a token. It returns an error when the context expires or is canceled before token acquisition.
