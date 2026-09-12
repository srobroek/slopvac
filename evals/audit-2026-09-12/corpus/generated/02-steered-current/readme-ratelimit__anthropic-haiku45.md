# gatekeep

A Go token-bucket rate limiter that enforces limits per key, backed by Redis or in-memory storage, with optional HTTP middleware.

## Install

```bash
go get github.com/user/gatekeep
```

## Usage

Create a limiter, then call `Allow` to check if a request is permitted, or `Wait` to block until it is.

```go
package main

import (
	"github.com/user/gatekeep"
)

func main() {
	limiter := gatekeep.NewMemoryLimiter(&gatekeep.Limiter{
		Rate:  10,
		Burst: 20,
		TTL:   time.Hour,
	})

	key := "user-123"
	if limiter.Allow(key) {
		// Request allowed
	}
}
```

## Examples

### Check if a request is allowed

```go
limiter := gatekeep.NewMemoryLimiter(&gatekeep.Limiter{
	Rate:  5,
	Burst: 10,
	TTL:   time.Minute,
})

if limiter.Allow("api-user-id") {
	fmt.Println("Request permitted")
} else {
	fmt.Println("Rate limit exceeded")
}
```

### Wait until a request is allowed

```go
ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
defer cancel()

err := limiter.Wait(ctx, "api-user-id")
if err != nil {
	fmt.Println("Context canceled or timed out")
	return
}
// Request allowed after waiting
```

### Use Redis as the backing store

```go
client := redis.NewClient(&redis.Options{Addr: "localhost:6379"})

limiter := gatekeep.NewRedisLimiter(client, &gatekeep.Limiter{
	Rate:  100,
	Burst: 200,
	TTL:   time.Hour,
})

allowed := limiter.Allow("endpoint-user")
```

### Enforce limits in HTTP handlers

```go
limiter := gatekeep.NewMemoryLimiter(&gatekeep.Limiter{
	Rate:  10,
	Burst: 20,
	TTL:   time.Minute,
})

mux := http.NewServeMux()
mux.HandleFunc("/api/data", gatekeep.Middleware(limiter, extractUserID)(handleData))

http.ListenAndServe(":8080", mux)

func handleData(w http.ResponseWriter, r *http.Request) {
	w.WriteHeader(http.StatusOK)
	w.Write([]byte("OK"))
}

func extractUserID(r *http.Request) string {
	return r.Header.Get("X-User-ID")
}
```

## Configuration

The `Limiter` struct configures rate limiting behavior:

| Field | Type | Effect |
|-------|------|--------|
| `Rate` | `int64` | Tokens added per second. |
| `Burst` | `int64` | Maximum tokens the bucket holds. |
| `TTL` | `time.Duration` | Duration before an unused key expires. |

## License

MIT
