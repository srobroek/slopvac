# gatekeep

A Go token-bucket rate limiter with per-key buckets, an in-memory store, a Redis store, and a `net/http` middleware.

## Install

```sh
go get github.com/gatekeep/gatekeep
```

gatekeep requires Go 1.21 or later. The Redis store imports `github.com/redis/go-redis/v9`, which provides the Redis client.

## Usage

Create a `Limiter` with a store, then call `Allow` with the key you want to limit:

```go
package main

import (
	"fmt"
	"time"

	"github.com/gatekeep/gatekeep"
)

func main() {
	limiter := gatekeep.New(gatekeep.Config{
		Rate:  10,
		Burst: 20,
		TTL:   10 * time.Minute,
		Store: gatekeep.NewMemoryStore(),
	})

	for i := 0; i < 25; i++ {
		ok, err := limiter.Allow("user:42")
		if err != nil {
			panic(err)
		}
		fmt.Printf("request %d allowed=%v\n", i, ok)
	}
}
```

`Rate: 10` refills the bucket at 10 tokens per second. `Burst: 20` caps the bucket at 20 tokens, so the first 20 calls in the loop return `true` and the remaining 5 return `false`.

## Examples

Each example below has a runnable counterpart under `examples/` in the repository.

### Block until a token is free

`Wait` blocks until the bucket for the key has a token, then takes it. It returns the context error if the context is cancelled or its deadline passes first.

```go
ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
defer cancel()

if err := limiter.Wait(ctx, "user:42"); err != nil {
	log.Printf("not allowed within 2s: %v", err)
	return
}
doWork()
```

### Limit HTTP handlers by client IP

`Middleware` wraps an `http.Handler`. It derives the key with the function you pass, calls `Allow`, and responds `429 Too Many Requests` when the call returns `false`.

```go
limiter := gatekeep.New(gatekeep.Config{
	Rate:  5,
	Burst: 10,
	TTL:   time.Minute,
	Store: gatekeep.NewMemoryStore(),
})

keyByIP := func(r *http.Request) string {
	host, _, err := net.SplitHostPort(r.RemoteAddr)
	if err != nil {
		return r.RemoteAddr
	}
	return host
}

mux := http.NewServeMux()
mux.HandleFunc("/search", searchHandler)

http.ListenAndServe(":8080", gatekeep.Middleware(limiter, keyByIP)(mux))
```

The 429 response carries a `Retry-After` header in whole seconds, rounded up from the wait until the next token.

### Share buckets across processes with Redis

`NewRedisStore` keeps each bucket in one Redis hash and updates it with a Lua script, so two processes limiting the same key share one bucket.

```go
rdb := redis.NewClient(&redis.Options{Addr: "localhost:6379"})

limiter := gatekeep.New(gatekeep.Config{
	Rate:  100,
	Burst: 200,
	TTL:   time.Hour,
	Store: gatekeep.NewRedisStore(rdb, "gatekeep:"),
})

ok, err := limiter.Allow("tenant:acme")
```

The second argument is a key prefix. With the prefix `gatekeep:`, the key `tenant:acme` becomes the Redis key `gatekeep:tenant:acme`.

`Allow` and `Wait` return an error when the Redis command fails. gatekeep does not fall back to a local bucket, so decide in your own code whether a Redis outage should allow or reject the request.

## Configuration

`Config` fields, passed to `gatekeep.New`:

| Name | Type | Default | Effect |
| --- | --- | --- | --- |
| `Rate` | `float64` | `0` | Tokens added per second. `0` rejects every call to `Allow`. |
| `Burst` | `int` | `0` | Maximum tokens a bucket holds, and the largest allowed spike. `0` rejects every call to `Allow`. |
| `TTL` | `time.Duration` | `0` | Idle time after which a bucket is discarded. `0` means buckets are never discarded. |
| `Store` | `Store` | `nil` | Bucket storage. `nil` makes `New` panic. |
| `Clock` | `func() time.Time` | `time.Now` | Time source used for refill. Set it to a fake clock in tests. |

`TTL` bounds memory in `NewMemoryStore`, which deletes a bucket after it stays idle for `TTL`. `NewRedisStore` sets `TTL` as the expiry on each bucket key. A bucket recreated after expiry starts full, at `Burst` tokens.

### Store interface

Implement `Store` to hold buckets somewhere else:

```go
type Store interface {
	Take(ctx context.Context, key string, cfg Config, now time.Time) (ok bool, retryAfter time.Duration, err error)
}
```

`Take` removes one token and reports whether it succeeded. When `ok` is `false`, `retryAfter` is the duration until the bucket holds one token. `Wait` sleeps for `retryAfter` and calls `Take` again.

## License

MIT. See [LICENSE](LICENSE).
