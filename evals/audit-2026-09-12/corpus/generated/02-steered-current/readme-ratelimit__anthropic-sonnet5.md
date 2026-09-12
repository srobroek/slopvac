# gatekeep

A Go library for token-bucket rate limiting with per-key buckets, backed by Redis or an in-memory store.

## Install

```
go get github.com/gatekeep/gatekeep
```

## Usage

```go
package main

import (
	"context"
	"fmt"
	"time"

	"github.com/gatekeep/gatekeep"
)

func main() {
	limiter := gatekeep.New(gatekeep.Limiter{
		Rate:  10,              // tokens added per second
		Burst: 20,              // maximum tokens in a bucket
		TTL:   5 * time.Minute, // bucket eviction after inactivity
	}, gatekeep.NewMemoryStore())

	if limiter.Allow("user:123") {
		fmt.Println("request allowed")
	}
}
```

## Configuration

| Name    | Type            | Default | Effect                                                        |
|---------|-----------------|---------|----------------------------------------------------------------|
| `Rate`  | `float64`       | none    | Tokens added to a bucket per second.                          |
| `Burst` | `int`           | none    | Maximum tokens a bucket can hold; caps burst request size.    |
| `TTL`   | `time.Duration` | none    | Idle duration after which a store removes an unused bucket.   |

`Rate`, `Burst`, and `TTL` are required; `gatekeep.New` panics if any is zero.

## Examples

### Allow: non-blocking check

`Allow(key)` reports whether a request tied to `key` may proceed, consuming one token if it does.

```go
limiter := gatekeep.New(gatekeep.Limiter{Rate: 5, Burst: 10, TTL: time.Minute}, gatekeep.NewMemoryStore())

for i := 0; i < 3; i++ {
	if limiter.Allow("ip:203.0.113.5") {
		fmt.Println("served request", i)
	} else {
		fmt.Println("rejected request", i)
	}
}
```

### Wait: blocking until a token is available

`Wait(ctx, key)` blocks until a token for `key` is available or `ctx` is canceled, then returns an error from `ctx.Err()` in the canceled case.

```go
limiter := gatekeep.New(gatekeep.Limiter{Rate: 2, Burst: 2, TTL: time.Minute}, gatekeep.NewMemoryStore())

ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
defer cancel()

if err := limiter.Wait(ctx, "job:batch-42"); err != nil {
	fmt.Println("gave up waiting:", err)
} else {
	fmt.Println("token acquired")
}
```

### Redis store: shared buckets across processes

`gatekeep.NewRedisStore` stores bucket state in Redis, so multiple processes share the same per-key limits.

```go
import "github.com/redis/go-redis/v9"

rdb := redis.NewClient(&redis.Options{Addr: "localhost:6379"})
store := gatekeep.NewRedisStore(rdb)

limiter := gatekeep.New(gatekeep.Limiter{
	Rate:  100,
	Burst: 200,
	TTL:   10 * time.Minute,
}, store)

limiter.Allow("api-key:abc123")
```

This example requires a Redis server reachable at `localhost:6379`.

### Middleware: net/http

`gatekeep.Middleware` wraps an `http.Handler` and applies `Allow` per request, keyed by a function you supply. It returns `429 Too Many Requests` when a key has no available token.

```go
mux := http.NewServeMux()
mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
	w.Write([]byte("ok"))
})

limiter := gatekeep.New(gatekeep.Limiter{Rate: 1, Burst: 5, TTL: time.Minute}, gatekeep.NewMemoryStore())

handler := gatekeep.Middleware(limiter, func(r *http.Request) string {
	return r.RemoteAddr
})(mux)

http.ListenAndServe(":8080", handler)
```

## Dependencies

The Redis store requires `github.com/redis/go-redis/v9` at runtime; the in-memory store has no external dependency.

## License

MIT
