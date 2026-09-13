# gatekeep

`gatekeep` is a Go library that implements token-bucket rate limiting with per-key buckets.

The library provides:

- `Allow(key)` for an immediate admission decision.
- `Wait(ctx, key)` for context-aware waiting.
- A `Limiter` configuration struct with `Rate`, `Burst`, and `TTL`.
- An in-memory store.
- A Redis store.
- Middleware for `net/http`.

## Configuration

Configure each limiter with these `Limiter` fields:

| Field | Purpose |
|---|---|
| `Rate` | Controls token replenishment for each key. |
| `Burst` | Controls the maximum token capacity for each key. |
| `TTL` | Controls the lifetime of inactive key state. |

The package does not specify default values for these fields in this documentation.

## Check a key

Call `Allow` when the caller needs an immediate decision:

```go
// Conceptual example.
if !limiter.Allow(key) {
	// Reject the operation.
}
```

`Allow(key)` returns whether the key can consume a token.

## Wait for capacity

Call `Wait` when the caller can wait for capacity:

```go
// Conceptual example.
if err := limiter.Wait(ctx, key); err != nil {
	// Stop when the context ends.
}
```

`Wait(ctx, key)` uses the supplied context to control the wait.

## Select a store

The library provides two store categories:

- The in-memory store keeps bucket state in process memory.
- The Redis store keeps bucket state in Redis.

Use the in-memory store when one process owns the rate-limit state. Use the Redis store when multiple processes must share that state.

The package's constructor and store-selection signatures are not included here because the available API information does not define their names or parameters.

## Add HTTP middleware

The library provides middleware for `net/http`.

Use that middleware to apply a configured limiter to an HTTP handler. The middleware's exported function name and key-selection parameters are not included here because the available API information does not define their signatures.

## API summary

| API | Purpose |
|---|---|
| `Allow(key)` | Make an immediate rate-limit decision. |
| `Wait(ctx, key)` | Wait for capacity under a context. |
| `Limiter` | Configure `Rate`, `Burst`, and `TTL`. |
| In-memory store | Store bucket state in process memory. |
| Redis store | Store bucket state in Redis. |
| `net/http` middleware | Apply rate limiting to HTTP handlers. |
