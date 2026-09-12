# gatekeep

`gatekeep` provides token-bucket rate limiting for Go applications. It maintains an independent bucket for each key and supports in-memory or Redis-backed storage.

## Install

```bash
go get github.com/sjors/gatekeep
```

## Usage

Create a limiter with a store, then call `Allow` for immediate decisions.

```go
package main

import (
	"log"
	"time"

	"github.com/sjors/gatekeep"
)

func main() {
	store := gatekeep.NewMemoryStore()

	limiter := gatekeep.NewLimiter(store, gatekeep.Limiter{
		Rate:  10,
		Burst: 20,
		TTL:   time.Minute,
	})

	if !limiter.Allow("user:42") {
		log.Println("rate limit exceeded")
		return
	}

	log.Println("request allowed")
}
```

Each key receives an independent token bucket. The `Rate` value controls token replenishment, and `Burst` controls the maximum number of tokens in a bucket.

### Wait for capacity

Use `Wait` when a caller should wait for a token instead of receiving an immediate rejection.

```go
ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
defer cancel()

if err := limiter.Wait(ctx, "user:42"); err != nil {
	log.Printf("request could not proceed: %v", err)
	return
}

log.Println("request allowed")
```

`Wait` returns when the key has capacity or when the context ends. The method returns the context error when cancellation or a deadline prevents the wait from completing.

## HTTP middleware

Wrap an `http.Handler` to rate-limit requests by key.

```go
package main

import (
	"net/http"
	"time"

	"github.com/sjors/gatekeep"
)

func main() {
	store := gatekeep.NewMemoryStore()

	limiter := gatekeep.NewLimiter(store, gatekeep.Limiter{
		Rate:  100,
		Burst: 200,
		TTL:   time.Minute,
	})

	handler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusNoContent)
	})

	rateLimited := gatekeep.Middleware(limiter, func(r *http.Request) string {
		return r.Header.Get("Authorization")
	})

	http.ListenAndServe(":8080", rateLimited(handler))
}
```

The middleware uses the key returned by the key function for each request. Configure the key function to match the identity that your application limits, such as a user ID, API key, or client address.

## Redis storage

Use the Redis store when multiple application instances must share rate-limit state.

```go
store := gatekeep.NewRedisStore(redisClient)

limiter := gatekeep.NewLimiter(store, gatekeep.Limiter{
	Rate:  100,
	Burst: 200,
	TTL:   time.Minute,
})
```

The Redis store keeps buckets outside the application process. Each application instance must use the same Redis deployment to share buckets.

## Configuration

| Name | Type | Default | Effect |
|---|---|---:|---|
| `Rate` | `float64` | `0` | Tokens added to each key's bucket per second. |
| `Burst` | `int` | `0` | Maximum tokens held by each key's bucket. |
| `TTL` | `time.Duration` | `0` | Duration before an inactive key's stored bucket expires. |

Set `Burst` to the maximum number of requests that a key can allow immediately. Set `TTL` to the period after which inactive keys can be removed from storage.

## Stores

`gatekeep` provides two store implementations:

- `MemoryStore` keeps buckets in the local process.
- `RedisStore` keeps buckets in Redis for shared state across processes.

Use `MemoryStore` when one process owns the rate-limit state. Use `RedisStore` when multiple processes must enforce the same limits.

## License

See the repository license file.
