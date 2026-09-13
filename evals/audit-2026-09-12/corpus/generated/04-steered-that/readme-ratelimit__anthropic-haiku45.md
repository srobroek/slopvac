# gatekeep

A Go rate limiter that enforces per-key token buckets via Redis or in-memory storage and provides `net/http` middleware.

## Install

```sh
go get github.com/your-org/gatekeep
```

## Usage

Create a `Limiter` to set rate and burst capacity:

```go
limiter := &gatekeep.Limiter{
	Rate:  10,  // 10 requests per second
	Burst: 20,  // allow up to 20 in one second
	TTL:   5 * time.Minute,
}
```

Store the limiter in Redis or memory, then call `Allow` to check immediately or `Wait` to block:

```go
store := gatekeep.NewRedisStore(redisClient, limiter)
// or:
store := gatekeep.NewMemoryStore(limiter)

// Check without blocking
if store.Allow("user123") {
	// Request is allowed
}

// Block until allowed or context cancels
err := store.Wait(ctx, "user123")
if err != nil {
	// Context cancelled or deadline exceeded
}
```

## Examples

### Per-user rate limiting

Enforce a 5-request-per-second limit on each user account:

```go
limiter := &gatekeep.Limiter{
	Rate:  5,
	Burst: 10,
	TTL:   1 * time.Minute,
}
store := gatekeep.NewMemoryStore(limiter)

http.HandleFunc("/api/query", func(w http.ResponseWriter, r *http.Request) {
	userID := r.Header.Get("X-User-ID")
	if !store.Allow(userID) {
		http.Error(w, "rate limit exceeded", http.StatusTooManyRequests)
		return
	}
	// Process the request
})
```

### Wait with timeout

Let slow clients queue up until the limit allows them:

```go
ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
defer cancel()

err := store.Wait(ctx, "api_key_" + apiKey)
if err != nil {
	http.Error(w, "rate limit timeout", http.StatusTooManyRequests)
	return
}
// Proceed with the request
```

### HTTP middleware

Wrap a handler with per-IP rate limiting:

```go
handler := gatekeep.Middleware(
	http.HandlerFunc(myHandler),
	gatekeep.NewRedisStore(redisClient, &gatekeep.Limiter{
		Rate:  100,
		Burst: 200,
		TTL:   1 * time.Hour,
	}),
	func(r *http.Request) string {
		return r.Header.Get("X-Forwarded-For")
	},
)
http.Handle("/api/", handler)
```

The middleware extracts a key from the request using the function you supply, calls `Allow`, and returns HTTP 429 if the limit is exceeded.

## Configuration

The `Limiter` struct governs rate and burst behavior:

| Field | Type | Effect |
|-------|------|--------|
| `Rate` | `float64` | Tokens added per second for each key. |
| `Burst` | `int64` | Maximum tokens a bucket can hold at once. |
| `TTL` | `time.Duration` | Time after the last request before a key's bucket is deleted. |

## License

See the LICENSE file.
