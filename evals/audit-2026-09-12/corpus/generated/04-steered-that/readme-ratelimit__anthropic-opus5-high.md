# gatekeep

A Go token-bucket rate limiter with per-key buckets, an in-memory store, a Redis store, and `net/http` middleware.

## Install

```
go get github.com/gatekeep/gatekeep
```

## Usage

```go
package main

import (
	"fmt"
	"time"

	"github.com/gatekeep/gatekeep"
)

func main() {
	lim := gatekeep.New(gatekeep.Limiter{
		Rate:  10,
		Burst: 20,
		TTL:   5 * time.Minute,
	}, gatekeep.NewMemoryStore())

	allowed, err := lim.Allow("user:42")
	if err != nil {
		panic(err)
	}
	fmt.Println(allowed)
}
```

`Allow(key)` removes one token from the bucket named by `key` and returns `true`. When the bucket holds no tokens, it returns `false` without waiting.

## Examples

### Block until a token is free

`Wait(ctx, key)` blocks until the bucket named by `key` has a token, then removes it. It returns the context error when the context is canceled or its deadline passes.

```go
ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
defer cancel()

if err := lim.Wait(ctx, "user:42"); err != nil {
	return err
}
// A token was consumed; proceed with the guarded work.
```

### Limit an HTTP handler by client IP

`Middleware` wraps an `http.Handler`. It calls `Allow` with the key returned by the `KeyFunc`. On `false` it writes status 429 and does not call the wrapped handler.

```go
lim := gatekeep.New(gatekeep.Limiter{
	Rate:  100,
	Burst: 200,
	TTL:   time.Hour,
}, gatekeep.NewMemoryStore())

mw := gatekeep.Middleware(lim, gatekeep.MiddlewareConfig{
	KeyFunc: func(r *http.Request) string {
		host, _, _ := net.SplitHostPort(r.RemoteAddr)
		return host
	},
})

http.ListenAndServe(":8080", mw(http.HandlerFunc(handler)))
```

### Share buckets across processes with Redis

The Redis store keeps every bucket in Redis, so that all processes pointing at one Redis instance draw from the same bucket per key. It requires `github.com/redis/go-redis/v9`, which provides the Redis client.

```go
rdb := redis.NewClient(&redis.Options{Addr: "localhost:6379"})

lim := gatekeep.New(gatekeep.Limiter{
	Rate:  50,
	Burst: 50,
	TTL:   10 * time.Minute,
}, gatekeep.NewRedisStore(rdb, "gatekeep:"))

allowed, err := lim.Allow("tenant:acme")
```

`NewRedisStore` takes a key prefix as its second argument. gatekeep prepends the prefix to every bucket key it writes.

The in-memory store never returns an error from `Allow`. The Redis store returns the underlying client error when the round trip fails.

## Configuration

`Limiter` holds the bucket parameters. One `Limiter` value governs every key in the store.

| Name | Type | Default | Effect |
| --- | --- | --- | --- |
| `Rate` | `float64` | `0` | Tokens added per second. `0` rejects every call to `Allow`. |
| `Burst` | `int` | `0` | Bucket capacity, and the number of tokens a fresh bucket starts with. `0` rejects every call to `Allow`. |
| `TTL` | `time.Duration` | `0` | Idle time after which a bucket is deleted. `0` keeps buckets for the process lifetime, or for the Redis key lifetime. |

`MiddlewareConfig` controls the `net/http` wrapper.

| Name | Type | Default | Effect |
| --- | --- | --- | --- |
| `KeyFunc` | `func(*http.Request) string` | `r.RemoteAddr` | Returns the bucket key for a request. |
| `OnLimit` | `http.Handler` | writes `429 Too Many Requests` | Handles a request whose bucket is empty. |
| `OnError` | `func(http.ResponseWriter, *http.Request, error)` | writes `500 Internal Server Error` | Handles a store error from `Allow`. |

## License

MIT
