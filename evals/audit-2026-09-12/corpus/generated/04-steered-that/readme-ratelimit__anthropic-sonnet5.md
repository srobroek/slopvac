# gatekeep

gatekeep is a Go library for per-key token-bucket rate limiting, with in-memory and Redis stores and an `net/http` middleware.

## Install

```
go get github.com/gatekeep-go/gatekeep
```

## Usage

The following program creates an in-memory limiter and checks whether key `user-42` may proceed.

```go
package main

import (
	"fmt"

	"github.com/gatekeep-go/gatekeep"
)

func main() {
	limiter := gatekeep.New(gatekeep.NewMemoryStore(), gatekeep.Limiter{
		Rate:  5,
		Burst: 10,
	})

	if limiter.Allow("user-42") {
		fmt.Println("request allowed")
	} else {
		fmt.Println("request denied")
	}
}
```

Allow reports whether key has an available token and consumes one token if it does.

## Examples

### Redis store

The Redis store shares buckets across processes through a Redis instance. gatekeep imports `github.com/redis/go-redis/v9` for the Redis store.

```go
package main

import (
	"time"

	"github.com/redis/go-redis/v9"
	"github.com/gatekeep-go/gatekeep"
	gkredis "github.com/gatekeep-go/gatekeep/redis"
)

func main() {
	client := redis.NewClient(&redis.Options{Addr: "localhost:6379"})
	store := gkredis.NewStore(client)

	limiter := gatekeep.New(store, gatekeep.Limiter{
		Rate:  100,
		Burst: 200,
		TTL:   10 * time.Minute,
	})

	limiter.Allow("api-key-abc")
}
```

### Blocking with Wait

Wait blocks until key has an available token or ctx is done, whichever occurs first.

```go
ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
defer cancel()

if err := limiter.Wait(ctx, "user-42"); err != nil {
	return err
}
```

Wait returns `ctx.Err()` when ctx ends before a token becomes available.

### HTTP middleware

Middleware wraps an `http.Handler` and returns HTTP 429 for a request whose key has no available token.

```go
package main

import (
	"net/http"

	"github.com/gatekeep-go/gatekeep"
)

func main() {
	limiter := gatekeep.New(gatekeep.NewMemoryStore(), gatekeep.Limiter{
		Rate:  10,
		Burst: 20,
	})

	mux := http.NewServeMux()
	mux.HandleFunc("/api", apiHandler)

	wrapped := gatekeep.Middleware(limiter, func(r *http.Request) string {
		return r.RemoteAddr
	})(mux)

	http.ListenAndServe(":8080", wrapped)
}
```

`keyFunc` extracts the rate-limit key from each request. This example uses the client's remote address.

## Configuration

`Limiter` configures a limiter's rate, burst size, and bucket eviction time.

| Field | Type | Default | Effect |
|---|---|---|---|
| `Rate` | `float64` | none, required | Number of tokens gatekeep adds to each bucket per second. |
| `Burst` | `int` | none, required | Maximum tokens a bucket holds. Caps the size of the largest allowed burst. |
| `TTL` | `time.Duration` | `0` | Idle time before gatekeep evicts a bucket. A value of `0` disables eviction. |

## License

gatekeep is released under the MIT License. See LICENSE for the full text.
