# gatekeep

A Go library for token-bucket rate limiting with per-key buckets, backed by Redis or memory.

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

	"github.com/gatekeep/gatekeep"
)

func main() {
	limiter := gatekeep.New(gatekeep.Config{
		Rate:  10,               // tokens added per second
		Burst: 20,               // maximum tokens in a bucket
		TTL:   5 * time.Minute,  // bucket eviction after no activity
	}, gatekeep.NewMemoryStore())

	if limiter.Allow("user:42") {
		fmt.Println("request allowed")
	}
}
```

`Allow(key)` checks the bucket for `key` and consumes one token if available. It returns `true` when a token was consumed, `false` when the bucket is empty.

## Examples

### Block until a token is available

```go
ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
defer cancel()

if err := limiter.Wait(ctx, "user:42"); err != nil {
	// ctx expired before a token became available
	return err
}
// a token was consumed; proceed
```

`Wait(ctx, key)` blocks until a token is available or `ctx` is done. It returns `ctx.Err()` on cancellation or deadline expiry.

### Redis-backed store for multiple processes

```go
store, err := gatekeep.NewRedisStore(gatekeep.RedisOptions{
	Addr: "localhost:6379",
})
if err != nil {
	log.Fatal(err)
}

limiter := gatekeep.New(gatekeep.Config{
	Rate:  5,
	Burst: 10,
	TTL:   time.Minute,
}, store)
```

`NewRedisStore` shares bucket state across processes connected to the same Redis instance. `NewMemoryStore` keeps bucket state in the process and does not share it.

### HTTP middleware

```go
mux := http.NewServeMux()
mux.HandleFunc("/api", handler)

rateLimited := gatekeep.Middleware(limiter, func(r *http.Request) string {
	return r.RemoteAddr
})(mux)

http.ListenAndServe(":8080", rateLimited)
```

`Middleware(limiter, keyFunc)` wraps an `http.Handler`. It calls `keyFunc` to derive a bucket key from each request, then calls `Allow` on that key. When `Allow` returns `false`, the middleware writes HTTP status `429 Too Many Requests` and stops the request from reaching the wrapped handler.

## Configuration

| Name  | Type            | Default | Effect |
|-------|-----------------|---------|--------|
| Rate  | `float64`       | none, required | Tokens added to each bucket per second. |
| Burst | `int`           | none, required | Maximum tokens a bucket can hold; caps burst size. |
| TTL   | `time.Duration` | `0` (never expire) | Duration of inactivity after which a key's bucket is removed from the store. |

## License

MIT
