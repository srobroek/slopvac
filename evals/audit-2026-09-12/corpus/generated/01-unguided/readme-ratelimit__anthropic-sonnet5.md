# gatekeep

`gatekeep` is a Go library for rate limiting using the token-bucket algorithm, with per-key buckets so you can independently throttle requests by user, API key, IP address, or any other identifier you choose.

It ships with two storage backends — an in-memory store for single-instance services and a Redis store for rate limiting across multiple instances — plus a ready-to-use middleware for `net/http`.

## Features

- **Token-bucket algorithm** — smooth rate limiting that allows short bursts while enforcing a steady average rate.
- **Per-key buckets** — each key (user ID, API key, IP, etc.) gets its own independent bucket.
- **Pluggable storage** — use the built-in in-memory store or the Redis store for distributed deployments.
- **Blocking and non-blocking APIs** — check availability immediately with `Allow`, or block until a token is available with `Wait`.
- **`net/http` middleware** — drop-in request throttling for HTTP servers.

## Installation

```sh
go get github.com/example/gatekeep
```

(Replace the import path above with the actual module path for your fork or vendored copy.)

## Core concepts

A `Limiter` controls how tokens are added to and drawn from buckets. Each distinct key gets its own bucket, backed by whichever store you configure.

```go
type Limiter struct {
    Rate  float64       // tokens added per second
    Burst int           // maximum tokens a bucket can hold
    TTL   time.Duration // how long an idle bucket is retained by the store
}
```

- **`Rate`** is the sustained throughput you want to allow, in tokens per second (e.g., `10` allows an average of 10 requests/second per key).
- **`Burst`** is the bucket capacity — the maximum number of tokens that can accumulate, which is also the largest burst of requests a key can make instantly.
- **`TTL`** tells the store when it may forget about a key's bucket after it's gone idle. This keeps memory (or Redis keys) from growing without bound as new keys appear. Set it comfortably longer than the time it takes a bucket to refill from empty to full.

Every request against a key consumes one token. If a token is available, the request is allowed and the token is removed from the bucket. If not, the request is either rejected (`Allow`) or the caller waits for one to become available (`Wait`).

## Quick start

### In-memory store

Use the in-memory store when your service runs as a single process, or when approximate, per-instance rate limiting is acceptable.

```go
package main

import (
    "fmt"
    "time"

    "github.com/example/gatekeep"
)

func main() {
    store := gatekeep.NewMemoryStore()

    limiter := gatekeep.Limiter{
        Rate:  5,               // 5 tokens/sec
        Burst: 10,               // allow bursts up to 10
        TTL:   5 * time.Minute,  // forget idle keys after 5 minutes
    }

    gk := gatekeep.New(store, limiter)

    if gk.Allow("user:42") {
        fmt.Println("request allowed")
    } else {
        fmt.Println("request denied")
    }
}
```

### Redis store

Use the Redis store when rate limits must be enforced consistently across multiple instances of your service.

```go
package main

import (
    "context"
    "time"

    "github.com/example/gatekeep"
    "github.com/redis/go-redis/v9"
)

func main() {
    rdb := redis.NewClient(&redis.Options{
        Addr: "localhost:6379",
    })

    store := gatekeep.NewRedisStore(rdb)

    limiter := gatekeep.Limiter{
        Rate:  20,
        Burst: 40,
        TTL:   10 * time.Minute,
    }

    gk := gatekeep.New(store, limiter)

    ctx := context.Background()
    if err := gk.Wait(ctx, "api-key:abc123"); err != nil {
        // ctx was canceled or timed out before a token became available
        panic(err)
    }

    // proceed with the request
}
```

## API

### `Allow(key string) bool`

Attempts to consume one token from the bucket identified by `key`. Returns `true` if a token was available and consumed, `false` otherwise. `Allow` never blocks — use it when you want to reject excess requests immediately (e.g., returning HTTP 429).

```go
if !gk.Allow(key) {
    http.Error(w, "rate limit exceeded", http.StatusTooManyRequests)
    return
}
```

### `Wait(ctx context.Context, key string) error`

Blocks until a token becomes available for `key`, or until `ctx` is canceled or its deadline is exceeded. Returns `nil` once a token has been consumed, or the context's error if it was canceled first. Use `Wait` when it's acceptable to delay a request rather than reject it outright — for example, when smoothing out background job throughput.

```go
ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
defer cancel()

if err := gk.Wait(ctx, key); err != nil {
    // gave up waiting for a token
    return err
}
```

### `Limiter`

Configuration passed to `gatekeep.New` (or attached per-key, depending on your setup). See [Core concepts](#core-concepts) above for what `Rate`, `Burst`, and `TTL` control.

## HTTP middleware

`gatekeep` includes middleware that rate-limits incoming `net/http` requests by a key you derive from each request — typically the client IP, an API key header, or an authenticated user ID.

```go
package main

import (
    "net/http"
    "time"

    "github.com/example/gatekeep"
)

func main() {
    store := gatekeep.NewMemoryStore()
    limiter := gatekeep.Limiter{
        Rate:  1,
        Burst: 5,
        TTL:   time.Minute,
    }
    gk := gatekeep.New(store, limiter)

    mux := http.NewServeMux()
    mux.HandleFunc("/", handler)

    keyFunc := func(r *http.Request) string {
        return r.Header.Get("X-API-Key")
    }

    wrapped := gatekeep.Middleware(gk, keyFunc)(mux)

    http.ListenAndServe(":8080", wrapped)
}

func handler(w http.ResponseWriter, r *http.Request) {
    w.Write([]byte("ok"))
}
```

By default, the middleware responds with `429 Too Many Requests` when a key has no tokens available. If `keyFunc` returns an empty string, requests fall back to being keyed by remote IP.

## Choosing between `Allow` and the middleware

- Use `Allow` or `Wait` directly when you need fine-grained control inside a handler or background worker — for instance, to rate-limit a specific downstream call rather than the whole request.
- Use the middleware when you want uniform, request-level throttling applied before your handlers run.

## Choosing a store

| Store | Use when |
|---|---|
| `MemoryStore` | Single-instance services, tests, or when slight inconsistency across restarts is acceptable. |
| `RedisStore` | Multiple service instances need to share the same rate limit state. |

Both stores implement the same interface, so you can switch between them without changing how you call `Allow`, `Wait`, or the middleware.

## License

See `LICENSE` in this repository.
