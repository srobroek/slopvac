# gatekeep

A simple, efficient token-bucket rate limiter for Go with per-key buckets, multiple storage backends, and net/http middleware support.

## Features

- **Token-bucket algorithm**: Proven rate limiting strategy with configurable rate and burst capacity
- **Per-key buckets**: Apply different limits to different resources, users, or IP addresses
- **Multiple stores**: Choose between Redis for distributed systems or in-memory for single instances
- **net/http middleware**: Drop-in middleware for HTTP servers
- **Context-aware waiting**: Use `Wait()` with context cancellation for graceful handling
- **Simple API**: Just `Allow()` and `Wait()` for most use cases

## Installation

```bash
go get github.com/yourorg/gatekeep
```

## Quick Start

### Basic Usage

```go
import "github.com/yourorg/gatekeep"

// Create a limiter with 10 requests per second and a burst of 20
limiter := gatekeep.NewMemoryLimiter(gatekeep.Limiter{
    Rate:  10,
    Burst: 20,
    TTL:   time.Minute,
})

// Check if a request is allowed (non-blocking)
if limiter.Allow("user:123") {
    // Handle request
} else {
    // Rate limit exceeded
}
```

### Waiting for Available Capacity

```go
ctx := context.Background()

// Wait until the next token is available or context is cancelled
if err := limiter.Wait(ctx, "user:123"); err != nil {
    // Context cancelled or deadline exceeded
    log.Print(err)
    return
}

// Proceed with request
```

## Configuration

### Limiter

The `Limiter` struct defines rate-limiting parameters:

```go
type Limiter struct {
    Rate  int64         // Requests per second (refill rate)
    Burst int64         // Maximum burst capacity (token bucket size)
    TTL   time.Duration // Time-to-live for idle keys in the store
}
```

- **Rate**: Tokens added to the bucket per second
- **Burst**: Maximum tokens the bucket can hold
- **TTL**: How long a bucket persists without activity (reduces memory usage in stores)

## Stores

### In-Memory Store

Best for single-instance applications or development.

```go
limiter := gatekeep.NewMemoryLimiter(gatekeep.Limiter{
    Rate:  100,
    Burst: 200,
    TTL:   5 * time.Minute,
})
```

Characteristics:
- No external dependencies
- Fast (in-process)
- Not shared across instances
- Memory grows with unique keys

### Redis Store

Best for distributed systems where multiple instances need shared limits.

```go
import "github.com/redis/go-redis/v9"

client := redis.NewClient(&redis.Options{
    Addr: "localhost:6379",
})

limiter := gatekeep.NewRedisLimiter(client, gatekeep.Limiter{
    Rate:  1000,
    Burst: 2000,
    TTL:   10 * time.Minute,
})
```

Characteristics:
- Shared across multiple application instances
- External dependency (Redis server)
- Slightly higher latency
- Redis handles TTL and cleanup

## HTTP Middleware

Apply rate limiting to HTTP handlers:

```go
import (
    "net/http"
    "github.com/yourorg/gatekeep"
)

limiter := gatekeep.NewMemoryLimiter(gatekeep.Limiter{
    Rate:  10,
    Burst: 20,
    TTL:   time.Minute,
})

// Middleware that rate limits by IP address
handler := gatekeep.HTTPMiddleware(limiter, func(r *http.Request) string {
    return r.RemoteAddr
})(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
    w.WriteHeader(http.StatusOK)
    w.Write([]byte("OK"))
}))

http.ListenAndServe(":8080", handler)
```

On rate limit exceeded, the middleware responds with HTTP 429 (Too Many Requests).

## Examples

### Rate Limit by User ID

```go
limiter := gatekeep.NewMemoryLimiter(gatekeep.Limiter{
    Rate:  5,  // 5 requests per second
    Burst: 10, // Allow 10 in a burst
    TTL:   time.Hour,
})

func handleRequest(userID string) error {
    if !limiter.Allow("user:" + userID) {
        return errors.New("rate limit exceeded")
    }
    // Process request
    return nil
}
```

### Rate Limit with Backoff

```go
func handleWithRetry(ctx context.Context, key string, maxRetries int) error {
    for attempt := 0; attempt < maxRetries; attempt++ {
        if limiter.Allow(key) {
            return process()
        }

        if err := limiter.Wait(ctx, key); err != nil {
            return fmt.Errorf("rate limit wait failed: %w", err)
        }
    }
    return errors.New("max retries exceeded")
}
```

### Different Limits for Different Endpoints

```go
strictLimiter := gatekeep.NewMemoryLimiter(gatekeep.Limiter{
    Rate:  1,
    Burst: 5,
    TTL:   time.Minute,
})

generousLimiter := gatekeep.NewMemoryLimiter(gatekeep.Limiter{
    Rate:  100,
    Burst: 500,
    TTL:   time.Minute,
})

// Apply strict limits to sensitive endpoints
http.Handle("/api/login", gatekeep.HTTPMiddleware(strictLimiter, keyFunc)(loginHandler))

// Apply generous limits to public endpoints
http.Handle("/api/public", gatekeep.HTTPMiddleware(generousLimiter, keyFunc)(publicHandler))
```

## API Reference

### `Allow(key string) bool`

Check if a request is allowed without blocking.

- **Parameters**: `key` — a unique identifier (user ID, IP address, etc.)
- **Returns**: `true` if allowed, `false` if rate limit exceeded
- **Behavior**: Non-blocking; always returns immediately

### `Wait(ctx context.Context, key string) error`

Wait until a token is available or the context is cancelled.

- **Parameters**: 
  - `ctx` — context that controls the wait (can be cancelled)
  - `key` — a unique identifier
- **Returns**: `nil` if token acquired, error if context cancelled/deadline exceeded
- **Behavior**: Blocks until a token is available

### `HTTPMiddleware(limiter Limiter, keyFunc func(*http.Request) string) func(http.Handler) http.Handler`

Wrap an HTTP handler with rate limiting.

- **Parameters**:
  - `limiter` — a `Limiter` instance
  - `keyFunc` — function to extract the rate-limit key from a request
- **Returns**: HTTP middleware function
- **Behavior**: Responds with 429 (Too Many Requests) if rate limited

## Performance Considerations

- **In-memory store**: O(1) operations; suitable for thousands of unique keys
- **Redis store**: Network latency applies; suitable for shared limits across instances
- **Key cardinality**: Consider TTL carefully; many unique keys consume memory or Redis resources

## Best Practices

1. **Choose appropriate Rate and Burst**: Rate is refill speed; Burst allows temporary spikes
2. **Use meaningful keys**: Include user ID, API key, or IP address in keys to apply limits appropriately
3. **Set reasonable TTL**: Balance memory usage against key persistence
4. **Handle context cancellation**: When using `Wait()`, always check context errors
5. **For distributed systems**: Use Redis; in-memory limits are per-instance only

## License

[Your License Here]
