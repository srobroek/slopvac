# gatekeep

`gatekeep` is a Go rate-limiting library based on the [token-bucket algorithm](https://en.wikipedia.org/wiki/Token_bucket). It supports independent buckets for arbitrary keys, including users, API tokens, IP addresses, or routes.

It provides:

- A `Limiter` configuration with `Rate`, `Burst`, and `TTL`
- `Allow(key)` for non-blocking rate-limit checks
- `Wait(ctx, key)` for context-aware waiting
- An in-memory store for single-process applications and tests
- A Redis-backed store for shared limits across processes
- Middleware for `net/http`

## Installation

```bash
go get github.com/your-org/gatekeep
```

## How it works

Each key has its own token bucket.

- `Rate` controls how quickly tokens are added to a bucket.
- `Burst` is the maximum number of tokens the bucket can hold.
- Each successful request consumes one token.
- `TTL` controls how long an inactive bucket remains in the store.

For example, a limiter configured with a rate of 10 requests per second and a burst of 20 allows short bursts of up to 20 requests, while sustaining approximately 10 requests per second over time.

## Quick start

Create a limiter with an in-memory store:

```go
package main

import (
	"fmt"
	"time"

	"github.com/your-org/gatekeep"
)

func main() {
	store := gatekeep.NewMemoryStore()

	limiter := gatekeep.NewLimiter(gatekeep.LimiterConfig{
		Rate:  10 * time.Second / 1, // 10 tokens per second
		Burst: 20,
		TTL:   10 * time.Minute,
	}, store)

	if limiter.Allow("user:42") {
		fmt.Println("request allowed")
		return
	}

	fmt.Println("rate limit exceeded")
}
```

The key is application-defined. Use a stable key for the identity whose traffic should be limited:

```go
limiter.Allow("user:42")
limiter.Allow("api-token:abc123")
limiter.Allow("ip:203.0.113.10")
```

These keys represent separate buckets.

## Configuration

`LimiterConfig` controls the behavior of every bucket:

```go
type LimiterConfig struct {
	Rate  time.Duration
	Burst int
	TTL   time.Duration
}
```

### `Rate`

`Rate` is the interval between tokens. For example:

```go
Rate: time.Second / 10, // 10 tokens per second
```

A smaller duration produces a higher rate.

### `Burst`

`Burst` is the maximum number of tokens a bucket can contain. It determines how many requests can be accepted immediately when tokens have accumulated.

```go
Burst: 20
```

`Burst` must be large enough to accommodate the traffic pattern you want to permit. A burst of `1` allows requests only at the configured rate and does not allow any additional short-term burst.

### `TTL`

`TTL` is the amount of time an inactive bucket remains in the store.

```go
TTL: 10 * time.Minute
```

A TTL prevents stores from growing indefinitely when keys are created dynamically. In a distributed deployment, use a TTL appropriate for your traffic and Redis configuration.

## Non-blocking checks with `Allow`

Use `Allow` when the caller should receive an immediate result:

```go
if !limiter.Allow("user:42") {
	// Return a rate-limit response.
	return
}

// Continue processing the request.
```

`Allow` returns:

- `true` when the key has a token available
- `false` when the bucket is empty

It does not wait for a token to become available.

## Waiting with `Wait`

Use `Wait` when a caller may wait for capacity:

```go
ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
defer cancel()

if err := limiter.Wait(ctx, "user:42"); err != nil {
	// The context was canceled or its deadline expired.
	return err
}

// A token is available; continue processing.
```

`Wait` respects the context:

- If a token is available, it returns immediately.
- If the bucket is empty, it waits until a token is available.
- If `ctx` is canceled or reaches its deadline first, it returns the context error.

Always pass a request-scoped context when using `Wait` in an HTTP handler.

## Stores

The limiter separates rate-limit state from rate-limit policy. A store holds the buckets, allowing the same limiter behavior to use different persistence strategies.

### In-memory store

The in-memory store is suitable for:

- Local development
- Tests
- Single-process services
- Limits that do not need to be shared between instances

```go
store := gatekeep.NewMemoryStore()

limiter := gatekeep.NewLimiter(gatekeep.LimiterConfig{
	Rate:  time.Second / 10,
	Burst: 20,
	TTL:   10 * time.Minute,
}, store)
```

Each process has its own buckets. If an application runs multiple replicas, requests routed to different replicas will not share a limit.

### Redis store

Use the Redis store when multiple application instances must share the same buckets:

```go
redisStore := gatekeep.NewRedisStore(redisClient, gatekeep.RedisStoreOptions{
	Prefix: "my-service:ratelimit",
})

limiter := gatekeep.NewLimiter(gatekeep.LimiterConfig{
	Rate:  time.Second / 10,
	Burst: 20,
	TTL:   10 * time.Minute,
}, redisStore)
```

The Redis store is appropriate when:

- The service runs multiple replicas.
- Requests may be distributed across different hosts.
- Rate-limit state must survive independently of an individual application process.

Use a shared Redis deployment that is available to every application instance. Configure a distinct key prefix when multiple services share the same Redis database.

## `net/http` middleware

`gatekeep` includes middleware for applying a limiter to HTTP requests.

The middleware needs a function that derives a rate-limit key from each request:

```go
package main

import (
	"net/http"

	"github.com/your-org/gatekeep"
)

func main() {
	store := gatekeep.NewMemoryStore()

	limiter := gatekeep.NewLimiter(gatekeep.LimiterConfig{
		Rate:  time.Second / 10,
		Burst: 20,
		TTL:   10 * time.Minute,
	}, store)

	keyFunc := func(r *http.Request) string {
		return r.Header.Get("Authorization")
	}

	handler := gatekeep.Middleware(limiter, keyFunc)(http.HandlerFunc(func(
		w http.ResponseWriter,
		r *http.Request,
	) {
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte("ok"))
	}))

	http.Handle("/api/", handler)
	_ = http.ListenAndServe(":8080", nil)
}
```

A common alternative is to limit by authenticated user ID:

```go
keyFunc := func(r *http.Request) string {
	userID := userIDFromContext(r.Context())
	if userID == "" {
		return "anonymous"
	}
	return "user:" + userID
}
```

If you limit by client IP, account for proxies and load balancers carefully. Do not trust forwarding headers unless they are set or sanitized by infrastructure you control.

## Returning rate-limit responses

When middleware rejects a request, return an HTTP `429 Too Many Requests` response. A handler or middleware wrapper can add application-specific headers and a response body:

```go
func rateLimitHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusTooManyRequests)
	_, _ = w.Write([]byte(`{"error":"rate limit exceeded"}`))
}
```

Clients should treat a `429` response as temporary and retry according to the service's documented policy. If your application exposes a retry delay, document whether it is approximate and how clients should interpret it.

## Choosing a key

A key defines the scope of a limit. Choose it based on the resource you want to protect.

| Goal | Example key |
| --- | --- |
| Per-user limit | `user:42` |
| Per-API-token limit | `token:abc123` |
| Per-tenant limit | `tenant:acme` |
| Per-IP limit | `ip:203.0.113.10` |
| Per-route and user | `route:/reports:user:42` |

Avoid using unbounded or sensitive values directly as keys. Normalize keys consistently, and consider hashing externally supplied identifiers before storing them if the key contents could expose sensitive data.

## Multiple limits

Create separate limiters when different resources need different policies:

```go
loginLimiter := gatekeep.NewLimiter(gatekeep.LimiterConfig{
	Rate:  time.Second,
	Burst: 5,
	TTL:   15 * time.Minute,
}, store)

apiLimiter := gatekeep.NewLimiter(gatekeep.LimiterConfig{
	Rate:  time.Second / 10,
	Burst: 20,
	TTL:   10 * time.Minute,
}, store)
```

For a route-specific limit, include the route in the key:

```go
key := "route:" + r.URL.Path + ":user:" + userID
if !apiLimiter.Allow(key) {
	// Reject the request.
}
```

## Testing

The in-memory store is useful for unit tests because it avoids external services:

```go
func TestRequestLimit(t *testing.T) {
	store := gatekeep.NewMemoryStore()

	limiter := gatekeep.NewLimiter(gatekeep.LimiterConfig{
		Rate:  time.Hour,
		Burst: 2,
		TTL:   time.Minute,
	}, store)

	if !limiter.Allow("test-key") {
		t.Fatal("first request should be allowed")
	}
	if !limiter.Allow("test-key") {
		t.Fatal("second request should be allowed")
	}
	if limiter.Allow("test-key") {
		t.Fatal("third request should be rejected")
	}
}
```

Use distinct keys between tests, or create a fresh store for each test, so state does not leak between cases.

## Operational considerations

- Use the Redis store when limits must be consistent across replicas.
- Set `TTL` for the maximum period that inactive keys should be retained.
- Keep the key format stable across application versions.
- Do not use a rate limiter as a replacement for authentication, authorization, input validation, or abuse detection.
- Choose `Burst` based on expected legitimate traffic; a very large burst can allow unexpectedly high short-term load.
- Apply limits close to the protected resource, and consider an additional edge or gateway limit for broad traffic protection.

## License

See the repository's license file for licensing information.
