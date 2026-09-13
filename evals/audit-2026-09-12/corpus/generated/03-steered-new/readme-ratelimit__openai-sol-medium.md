# gatekeep

`gatekeep` provides per-key token-bucket rate limiting for Go applications, Redis deployments, and `net/http` handlers.

## Usage

Configure a `Limiter` with `Rate`, `Burst`, and `TTL`.

Each key receives an independent token bucket. Calls for one key do not consume tokens from another key.

Use `Allow(key)` when the caller must receive an immediate decision.

Use `Wait(ctx, key)` when the caller can wait for a token. The context controls cancellation and deadlines.

## Stores

| Store | Scope | Use |
|---|---|---|
| In-memory store | One Go process | Keep buckets inside the application process. |
| Redis store | Processes using the same Redis data | Share per-key buckets across application instances. |

Choose the in-memory store when one process owns all rate-limit decisions. Choose the Redis store when multiple processes must share limits.

## HTTP middleware

The `net/http` middleware applies a limiter before invoking the wrapped handler.

Configure the middleware to derive a key from each request. Requests with the same key use the same token bucket.

## Configuration

| Name | Type | Effect |
|---|---|---|
| `Rate` | Rate value | Sets the token replenishment rate for each key. |
| `Burst` | Integer | Sets the maximum number of tokens available to each key. |
| `TTL` | Duration | Sets how long the store retains an inactive per-key bucket. |
