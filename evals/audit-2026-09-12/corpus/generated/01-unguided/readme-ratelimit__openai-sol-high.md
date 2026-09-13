# gatekeep

`gatekeep` is a Go token-bucket rate limiter with independent limits for each key. It supports:

- Immediate decisions with `Allow(key)`
- Context-aware waiting with `Wait(ctx, key)`
- In-memory storage for single-process applications
- Redis storage for distributed applications
- Rate-limiting middleware for `net/http`
- Automatic cleanup of inactive buckets with configurable TTLs

Use keys such as user IDs, tenant IDs, API keys, or normalized client addresses to decide which requests share a limit.

## Installation

```sh
go get <module-path>
```

Replace `<module-path>` with the module path used by your project.

## How it works

Each key receives an independent token bucket:

1. The bucket holds at most `Burst` tokens.
2. Each accepted operation consumes one token.
3. Tokens are replenished continuously at `Rate`.
4. When no token is available, `Allow` rejects immediately while `Wait` waits for one.
5. Inactive bucket state is removed after `TTL`.

For example, a rate of 10 tokens per second and a burst of 20 allows short spikes of up to 20 operations while maintaining a long-term rate of approximately 10 operations per second.

## Configuration

Create a limiter configuration with `Rate`, `Burst`, and `TTL`:

```go
cfg := gatekeep.Limiter{
	Rate:  10,
	Burst: 20,
	TTL:   15 * time.Minute,
}
```

| Field | Description |
| --- | --- |
| `Rate` | Sustained number of tokens added per second. |
| `Burst` | Maximum bucket capacity and maximum immediately available burst. |
| `TTL` | How long inactive per-key bucket state remains in the selected store. |

A bucket that expires is created again when its key is next used. The new bucket starts with the implementation's initial token capacity.

Choose a TTL that balances storage use against continuity:

- Short TTLs reduce memory or Redis usage for high-cardinality keys.
- Long TTLs preserve bucket state for clients that return infrequently.
- TTL does not change the configured refill rate or burst size.

## Checking immediately with `Allow`

Use `Allow` when an operation should be accepted or rejected without waiting:

```go
key := "tenant:acme"

if !limiter.Allow(key) {
	// Reject the operation or return HTTP 429.
	return
}

// Continue with the operation.
```

Calls using different keys consume tokens from different buckets:

```go
limiter.Allow("user:alice")
limiter.Allow("user:bob")
```

Traffic for `user:alice` does not consume tokens from `user:bob`.

## Waiting with `Wait`

Use `Wait` when the caller may pause until a token becomes available:

```go
ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
defer cancel()

if err := limiter.Wait(ctx, "worker:imports"); err != nil {
	// The context was canceled or its deadline expired.
	return err
}

return runImport()
```

`Wait` returns immediately when a token is available. Otherwise, it waits until either:

- A token becomes available, or
- The context is canceled or reaches its deadline.

Always use a bounded context when an indefinite wait would be unsafe.

## Storage backends

### In-memory store

The in-memory store is suitable for:

- Single-process services
- Command-line programs
- Local development
- Tests
- Limits that intentionally apply per process

Bucket state exists only in the current process and is lost when the process exits. When an application runs multiple replicas, each replica enforces its own independent limit.

Do not use the in-memory store when a limit must be shared across processes.

### Redis store

The Redis store is suitable for:

- Horizontally scaled services
- Multiple application instances
- Limits shared by workers and HTTP servers
- Bucket state that must survive application restarts

Point every application instance at the same Redis deployment and use the same key namespace when they must share limits.

Redis adds network and operational dependencies to each rate-limit decision. Configure connection timeouts and decide how the application should behave when Redis is unavailable:

- **Fail closed:** reject requests when the limiter cannot verify capacity.
- **Fail open:** allow requests to preserve availability.
- **Fallback locally:** temporarily use process-local limits.

Choose this policy according to whether protecting the downstream system or accepting traffic is more important.

## HTTP middleware

The `net/http` middleware applies `Allow` before passing a request to the next handler. Requests without an available token receive `429 Too Many Requests`.

A middleware setup needs:

1. A configured limiter
2. A backing store
3. A function that derives a stable key from each request
4. The `http.Handler` being protected

Common key sources include:

- Authenticated user ID
- Tenant or account ID
- API key identifier
- Route and tenant combination
- Normalized client address

Prefer authenticated identifiers over raw IP addresses:

```text
tenant:acme
user:42
api-key:9f83...
tenant:acme:route:/v1/reports
```

Avoid using secrets directly as keys. Hash or map API keys to non-sensitive identifiers before passing them to the limiter.

When deriving keys from client addresses, only trust forwarding headers such as `X-Forwarded-For` when they were added or sanitized by a trusted proxy.

## Choosing limits

Suppose an upstream service can safely process 100 requests per second per tenant and tolerate a brief burst of 200 requests:

```go
gatekeep.Limiter{
	Rate:  100,
	Burst: 200,
	TTL:   30 * time.Minute,
}
```

Start with values based on downstream capacity rather than average traffic. Monitor rejections and latency, then adjust:

- Increase `Rate` when sustained legitimate traffic is being limited.
- Increase `Burst` when short, harmless spikes are being rejected.
- Decrease `Burst` when spikes overload downstream dependencies.
- Decrease `TTL` when inactive keys consume excessive storage.

A large burst allows clients to spend accumulated capacity quickly. It should not be treated as merely a smoothing parameter.

## Key design

The key determines the scope of a limit. Keep key construction consistent across callers and application instances.

```go
func tenantKey(tenantID string) string {
	return "tenant:" + tenantID
}

func routeKey(tenantID, route string) string {
	return "tenant:" + tenantID + ":route:" + route
}
```

Good keys are:

- Stable for the lifetime of the identity
- Explicitly namespaced
- Free of credentials and personal data
- Bounded in size
- Derived from normalized input

Be careful with attacker-controlled keys. An unbounded number of unique keys can increase memory consumption or create large numbers of Redis entries. Validate or normalize key inputs and configure an appropriate TTL.

## `Allow` or `Wait`?

| Scenario | Recommended method |
| --- | --- |
| HTTP request that should be rejected when over limit | `Allow` |
| Background worker that may slow down | `Wait` |
| Interactive request with a strict latency budget | `Allow` |
| Batch process with a deadline | `Wait` with a bounded context |
| Protecting a dependency from queued work | Usually `Allow` |
| Smoothing outbound operations | `Wait` |

`Wait` introduces queuing into the caller. Ensure the number of waiting goroutines is bounded independently when traffic can grow without limit.

## Testing

Use the in-memory store in unit tests so tests do not require Redis. Configure small limits and bounded contexts to keep tests fast.

Test at least these cases:

- The first operation is allowed.
- Operations are rejected after the burst is exhausted.
- Capacity becomes available as tokens refill.
- Different keys use independent buckets.
- `Wait` stops when its context is canceled.
- Inactive bucket state expires after the configured TTL.
- HTTP middleware returns `429 Too Many Requests` when a key is limited.
- Redis-backed instances enforce one shared limit.

Avoid tests that depend on long sleeps. Prefer short deadlines or a controllable clock when the store supports one.

## Operational guidance

- Track allowed, rejected, waiting, and failed limiter operations.
- Include the limit name in metrics, but avoid unbounded per-key metric labels.
- Use separate key namespaces for unrelated limits.
- Set Redis command and connection timeouts.
- Monitor Redis latency, errors, and key count.
- Bound HTTP request durations even when using `Wait`.
- Document whether storage failures fail open or fail closed.
- Keep limiter configuration consistent across distributed instances.
