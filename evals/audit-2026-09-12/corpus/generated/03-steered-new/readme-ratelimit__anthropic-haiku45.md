# gatekeep

Token-bucket rate limiter for Go with per-key buckets, Redis or in-memory storage, and HTTP middleware.

## Install

```bash
go get github.com/you/gatekeep
```

## Usage

Create a limiter and call `Allow` to check whether a request can proceed.

```go
package main

import (
	"github.com/you/gatekeep"
)

func main() {
	limiter := gatekeep.New(gatekeep.Limiter{
		Rate:  10,        // tokens per second
		Burst: 20,        // maximum tokens in bucket
		TTL:   time.Hour, // bucket lifetime
		Store: gatekeep.NewMemoryStore(),
	})

	if limiter.Allow("user-123") {
		// Process request
	}
}
```

## Examples

### Block until a token is available

Call `Wait` to block until the next token is available for a key.

```go
ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
defer cancel()

err := limiter.Wait(ctx, "user-456")
if err != nil {
	log.Fatal(err)
}
// Process request
```

### Use Redis for distributed rate limiting

Pass a Redis store to share state across processes.

```go
limiter := gatekeep.New(gatekeep.Limiter{
	Rate:  5,
	Burst: 15,
	TTL:   time.Hour,
	Store: gatekeep.NewRedisStore(redisClient),
})
```

### Protect HTTP routes with middleware

Wrap a handler to rate-limit by IP or user header.

```go
handler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
	w.WriteHeader(http.StatusOK)
	w.Write([]byte("OK"))
})

limited := gatekeep.Middleware(limiter, func(r *http.Request) string {
	return r.Header.Get("X-User-ID")
})(handler)

http.ListenAndServe(":8080", limited)
```

The middleware returns HTTP 429 (Too Many Requests) when the bucket is empty.

## Configuration

| Name  | Type        | Default | Effect                                                   |
|-------|-------------|---------|----------------------------------------------------------|
| Rate  | `float64`   | —       | Tokens added per second to each key's bucket.            |
| Burst | `int64`     | —       | Maximum tokens in a bucket; requests above this are denied. |
| TTL   | `time.Duration` | —   | Time a bucket persists without new requests.            |
| Store | `Store`     | —       | Backend: `NewMemoryStore()` or `NewRedisStore(client)`. |

## License

Specify your license here.
