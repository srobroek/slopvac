# gatekeep

A Go token-bucket rate limiter with per-key buckets, an in-memory store, a Redis store, and `net/http` middleware.

## Install

```sh
go get github.com/example/gatekeep
```

Requires Go 1.22 or later. The Redis store imports `github.com/redis/go-redis/v9`, which provides the Redis client.

## Usage

Create a `Limiter` with a store, then call `Allow` with a key:

```go
package main

import (
	"fmt"
	"time"

	"github.com/example/gatekeep"
)

func main() {
	lim := gatekeep.New(gatekeep.Limiter{
		Rate:  10,
		Burst: 20,
		TTL:   10 * time.Minute,
		Store: gatekeep.NewMemoryStore(),
	})

	for i := 0; i < 3; i++ {
		fmt.Println(lim.Allow("user-42"))
	}
}
```

`Rate` is 10 tokens per second. `Burst` is 20, so the first 20 calls for `user-42` return `true` and later calls return `false` until the bucket refills.

## Examples

Each example below has a runnable counterpart under `examples/` in the repository.

### Block until a token is free

`Wait` blocks until the bucket for the key has a token, the context is cancelled, or the deadline passes. It returns the context error on cancellation.

```go
ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
defer cancel()

if err := lim.Wait(ctx, "user-42"); err != nil {
	log.Fatalf("rate limit wait: %v", err)
}
callUpstream()
```

`Wait` consumes one token when it returns `nil`. It consumes no token when it returns an error.

### Limit an HTTP handler by client IP

```go
lim := gatekeep.New(gatekeep.Limiter{
	Rate:  5,
	Burst: 10,
	TTL:   time.Minute,
	Store: gatekeep.NewMemoryStore(),
})

mux := http.NewServeMux()
mux.HandleFunc("/api", func(w http.ResponseWriter, r *http.Request) {
	w.Write([]byte("ok\n"))
})

http.ListenAndServe(":8080", gatekeep.Middleware(lim)(mux))
```

The middleware derives the key from `r.RemoteAddr` with the port stripped. A rejected request gets status `429`, a `Retry-After` header in whole seconds, and an empty body. The wrapped handler is not called.

### Key by API token instead of IP

`KeyFunc` replaces the default key derivation. Return an empty string to skip limiting for that request.

```go
mw := gatekeep.Middleware(lim, gatekeep.WithKeyFunc(func(r *http.Request) string {
	return r.Header.Get("X-Api-Key")
}))
```

### Share buckets across processes with Redis

```go
rdb := redis.NewClient(&redis.Options{Addr: "127.0.0.1:6379"})

lim := gatekeep.New(gatekeep.Limiter{
	Rate:  100,
	Burst: 200,
	TTL:   time.Hour,
	Store: gatekeep.NewRedisStore(rdb, "gatekeep:"),
})
```

`NewRedisStore` takes a client and a key prefix. Each bucket is one Redis hash at `<prefix><key>`. The store updates the bucket in a Lua script, so two processes sharing one Redis server cannot both spend the last token.

`RedisStore.Allow` returns `false` and a non-nil error when Redis is unreachable. Use `AllowErr` instead of `Allow` to read that error:

```go
ok, err := lim.AllowErr("user-42")
if err != nil {
	// Redis is unreachable; decide whether to fail open or closed.
}
```

## Configuration

`Limiter` fields:

| Name | Type | Default | Effect |
| --- | --- | --- | --- |
| `Rate` | `float64` | none, required | Tokens added per second. `New` panics when `Rate` is not greater than 0. |
| `Burst` | `int` | none, required | Bucket capacity, and the largest number of calls allowed at once. `New` panics when `Burst` is below 1. |
| `TTL` | `time.Duration` | `10 * time.Minute` | Idle time after which a key's bucket is discarded. |
| `Store` | `gatekeep.Store` | `NewMemoryStore()` | Where buckets live. |
| `Clock` | `func() time.Time` | `time.Now` | Time source for refill. Set it in tests to advance time without sleeping. |

`Middleware` options:

| Name | Type | Default | Effect |
| --- | --- | --- | --- |
| `WithKeyFunc` | `func(*http.Request) string` | client IP from `r.RemoteAddr` | Key for the request. An empty return value skips the limiter. |
| `WithStatusCode` | `int` | `429` | Status written to a rejected request. |
| `WithOnReject` | `http.Handler` | writes the status and `Retry-After` | Handler for a rejected request. It replaces the default response. |

### Store behavior

| Store | Bucket lifetime | Cross-process | Notes |
| --- | --- | --- | --- |
| `MemoryStore` | Swept every `TTL` | No | Holds buckets in a `map` behind a mutex. Call `Close` to stop the sweeper goroutine. |
| `RedisStore` | Redis key expiry set to `TTL` on each write | Yes | One round trip per `Allow`. Needs Redis 3.2 or later for `EVALSHA` with `TIME`. |

## Testing against a fixed clock

Set `Clock` to a function you control, and the limiter refills only when you move it:

```go
now := time.Unix(0, 0)
lim := gatekeep.New(gatekeep.Limiter{
	Rate:  1,
	Burst: 1,
	Store: gatekeep.NewMemoryStore(),
	Clock: func() time.Time { return now },
})

lim.Allow("k")        // true, spends the single token
lim.Allow("k")        // false
now = now.Add(time.Second)
lim.Allow("k")        // true
```

`RedisStore` reads time from the Redis server with `TIME`, so `Clock` does not affect it.

## License

MIT. See `LICENSE`.
