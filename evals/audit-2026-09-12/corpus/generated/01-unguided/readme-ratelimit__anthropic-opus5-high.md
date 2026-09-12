# gatekeep

A token-bucket rate limiter for Go, with per-key buckets, pluggable storage (in-memory or Redis), and a `net/http` middleware.

[![Go Reference](https://pkg.go.dev/badge/github.com/gatekeep-go/gatekeep.svg)](https://pkg.go.dev/github.com/gatekeep-go/gatekeep)

## Install

```sh
go get github.com/gatekeep-go/gatekeep
```

Requires Go 1.22 or later. The Redis store depends on [`github.com/redis/go-redis/v9`](https://github.com/redis/go-redis); the core package and the in-memory store have no third-party dependencies.

## Quick start

```go
package main

import (
	"log"
	"net/http"
	"time"

	"github.com/gatekeep-go/gatekeep"
)

func main() {
	gate, err := gatekeep.New(gatekeep.Limiter{
		Rate:  gatekeep.PerSecond(10), // sustained rate per key
		Burst: 20,                     // bucket capacity
		TTL:   10 * time.Minute,        // how long an idle bucket is kept
		Store: gatekeep.NewMemoryStore(),
	})
	if err != nil {
		log.Fatal(err)
	}
	defer gate.Close()

	ok, err := gate.Allow("user:42")
	if err != nil {
		log.Fatal(err)
	}
	if !ok {
		log.Println("user:42 is over its limit")
	}

	mux := http.NewServeMux()
	mux.HandleFunc("/api/search", search)

	handler := gatekeep.Middleware(gate, gatekeep.MiddlewareConfig{
		KeyFunc: gatekeep.KeyByRemoteIP,
		Headers: true,
	})(mux)

	log.Fatal(http.ListenAndServe(":8080", handler))
}
```

## How the limiter works

Each key gets its own bucket. A bucket holds up to `Burst` tokens and refills continuously at `Rate` tokens per second. A request takes one token: if a token is available the request is allowed, otherwise it is denied (`Allow`) or delayed (`Wait`).

Two numbers describe the shape of the limit:

- `Rate` is the throughput a key gets over a long window.
- `Burst` is how much unused allowance a key may accumulate and spend at once.

With `Rate: 10` and `Burst: 20`, a key that has been idle can fire 20 requests immediately, then settles into 10 requests per second. Setting `Burst` equal to `Rate` gives roughly one second of slack; setting it to `1` removes bursting entirely and spaces requests evenly.

Refill is computed from the elapsed time on read, not by a background ticker, so an idle key costs nothing until it is used again.

## Configuration

`Limiter` is a plain config struct. Pass it to `New`, which validates it and returns a `*Gate`.

| Field | Type | Meaning |
| --- | --- | --- |
| `Rate` | `float64` | Tokens added per second. Must be greater than 0. |
| `Burst` | `int` | Bucket capacity in tokens. Must be at least 1. |
| `TTL` | `time.Duration` | How long a bucket survives without traffic. Zero means `Burst/Rate` rounded up, with a one-minute floor. |
| `Store` | `Store` | Where bucket state lives. Defaults to a new in-memory store. |
| `Clock` | `Clock` | Time source. Defaults to the system clock. Override it in tests. |

Rate helpers convert human units to tokens per second:

```go
gatekeep.PerSecond(10) // 10
gatekeep.PerMinute(600) // 10
gatekeep.PerHour(3600) // 1
```

`New` returns `ErrInvalidConfig` (wrapped with the offending field) for a non-positive `Rate`, a `Burst` below 1, or a negative `TTL`.

### Choosing a TTL

`TTL` bounds memory in the in-memory store and key count in Redis. A bucket is dropped once it has been idle for `TTL`, and a dropped bucket is recreated full on the next request.

Set `TTL` to at least `Burst/Rate`, the time a bucket needs to refill from empty. A shorter TTL can forgive debt early: a key that empties its bucket and pauses for slightly longer than `TTL` starts over with a full bucket instead of a partly refilled one. Longer TTLs are safe and only cost storage.

## Deciding: `Allow` and `Wait`

```go
func (g *Gate) Allow(key string) (bool, error)
func (g *Gate) AllowN(ctx context.Context, key string, n int) (Decision, error)

func (g *Gate) Wait(ctx context.Context, key string) error
func (g *Gate) WaitN(ctx context.Context, key string, n int) error
```

`Allow` takes one token and reports whether it was granted. It is the right call for request admission, where rejecting is better than queueing. `Allow` uses `context.Background()` for the store call; with the Redis store, prefer `AllowN` so that a client disconnect or request deadline can cancel the round trip.

`AllowN` returns a `Decision` with the details a caller needs to explain itself:

```go
type Decision struct {
	OK         bool          // whether the tokens were granted
	Remaining  int           // whole tokens left after this call
	RetryAfter time.Duration // when the requested tokens will be available; 0 if OK
	ResetAfter time.Duration // when the bucket will be full again
}
```

Denied calls consume nothing, so a rejected client does not push its own recovery further away.

`Wait` blocks until a token is available for `key`, then returns `nil`. Use it for outbound work you control, such as pacing calls to a third-party API:

```go
for _, id := range ids {
	if err := gate.Wait(ctx, "upstream:billing"); err != nil {
		return err
	}
	if err := fetch(ctx, id); err != nil {
		return err
	}
}
```

`Wait` returns `ctx.Err()` if the context is cancelled or its deadline passes while waiting. If the wait would provably outlast a context deadline, `Wait` returns `context.DeadlineExceeded` immediately instead of sleeping. Requesting more than `Burst` tokens can never succeed, so `WaitN` rejects it with `ErrBurstExceeded` rather than blocking forever.

`Wait` polls: it computes the delay until the next token, sleeps, and retries. Waiters on the same key are therefore not served in arrival order, and a busy key can starve a long-running waiter. If you need ordering, put your own queue in front of a single waiter.

Both methods are safe for concurrent use from many goroutines.

## Stores

A `Gate` keeps no bucket state of its own. It delegates to a `Store`:

```go
type Store interface {
	Take(ctx context.Context, key string, req Request) (Decision, error)
	Close() error
}

type Request struct {
	Tokens int
	Rate   float64
	Burst  int
	TTL    time.Duration
	Now    time.Time
}
```

`Take` must apply refill and deduction as one atomic step per key. Implement the interface to back gatekeep with something else, such as Memcached or a SQL table.

`Gate.Close` closes the store it was given.

### In-memory store

```store
store := gatekeep.NewMemoryStore()
```

Buckets live in a sharded map guarded by per-shard mutexes, so unrelated keys rarely contend. A background sweeper removes buckets that have been idle for longer than `TTL`; `Close` stops it.

Options:

```go
store := gatekeep.NewMemoryStore(
	gatekeep.WithShards(64),               // default: 4 x GOMAXPROCS, rounded to a power of two
	gatekeep.WithSweepInterval(time.Minute), // default: TTL/4, clamped to [1s, 5m]
	gatekeep.WithMaxKeys(1_000_000),        // default: unlimited
)
```

With `WithMaxKeys`, the store evicts the least recently used bucket when the limit is reached. Eviction grants the evicted key a full bucket on its next request, so treat the cap as a memory backstop rather than part of the policy.

`store.Len()` reports the number of live buckets, which is useful for a gauge metric.

Each key holds one bucket: a timestamp, a token count, and the key itself. State is per process, so N replicas behind a load balancer enforce roughly N times the configured rate. Use Redis when the limit must be shared.

### Redis store

```go
rdb := redis.NewClient(&redis.Options{Addr: "localhost:6379"})

store := gatekeep.NewRedisStore(rdb,
	gatekeep.WithKeyPrefix("gk:prod:"), // default: "gatekeep:"
)
```

`NewRedisStore` accepts any `redis.UniversalClient`, including cluster and failover clients.

The store keeps one hash per key and updates it with a Lua script loaded through `EVALSHA`, so refill and deduction happen inside Redis without a round trip per step. The script reads the current time from Redis with `TIME`, which means all application instances share one clock and skew between them does not affect the result. Expiry is refreshed with `PEXPIRE` on every call, so idle keys disappear on their own and no sweeper is needed.

Every call touches exactly one key, which makes the script safe on Redis Cluster without hash tags. `Close` does not close the client you passed in; own its lifecycle yourself.

A store error is returned to the caller unchanged (wrapped in `ErrStore`), so you decide whether a Redis outage should reject traffic or let it through. The middleware makes that choice explicit; see `FailClosed` below.

## HTTP middleware

```go
func Middleware(g *Gate, cfg MiddlewareConfig) func(http.Handler) http.Handler
```

```go
handler := gatekeep.Middleware(gate, gatekeep.MiddlewareConfig{
	KeyFunc:    gatekeep.KeyByHeader("X-API-Key"),
	Headers:    true,
	FailClosed: false,
})(mux)
```

`MiddlewareConfig` fields:

| Field | Meaning |
| --- | --- |
| `KeyFunc` | `func(*http.Request) string` returning the bucket key. Defaults to `KeyByRemoteIP`. An empty key skips limiting for that request. |
| `Headers` | Add `RateLimit-Limit`, `RateLimit-Remaining`, and `RateLimit-Reset` to every response. Default `false`. |
| `FailClosed` | On a store error, reject with 503 instead of letting the request through. Default `false`. |
| `OnLimit` | Handler for rejected requests. Defaults to `429 Too Many Requests` with a `Retry-After` header. |
| `OnError` | Called with the request and the store error. Use it for logging; the response is still governed by `FailClosed`. |

Built-in key functions:

- `KeyByRemoteIP` uses the connection's remote address with the port stripped.
- `KeyByHeader(name)` uses a header value, falling back to the remote IP when the header is absent.
- `KeyByPath` uses the request path, for limiting an endpoint rather than a client.

`KeyByRemoteIP` reads `RemoteAddr` and ignores `X-Forwarded-For`, because a client can set that header freely. Behind a proxy you trust, resolve the client address in an earlier middleware or write a `KeyFunc` that reads the header your proxy sets and validates it.

Compose keys to limit on more than one dimension:

```go
KeyFunc: func(r *http.Request) string {
	return gatekeep.KeyByHeader("X-API-Key")(r) + "|" + r.URL.Path
}
```

The middleware calls `AllowN` with the request context, so a cancelled request does not leave a store call running.

### Several limits at once

A `Gate` carries one policy. For a burst limit and a daily quota, build one gate per policy and chain the middlewares:

```go
perSecond, _ := gatekeep.New(gatekeep.Limiter{Rate: gatekeep.PerSecond(20), Burst: 40, Store: store})
perDay, _ := gatekeep.New(gatekeep.Limiter{Rate: gatekeep.PerHour(500), Burst: 12_000, TTL: 48 * time.Hour, Store: store})

handler = gatekeep.Middleware(perSecond, cfg)(gatekeep.Middleware(perDay, cfg)(mux))
```

Give the gates different `WithKeyPrefix` values, or different key functions, so their buckets stay separate.

## Errors

| Error | Cause |
| --- | --- |
| `ErrInvalidConfig` | `New` rejected the `Limiter`. |
| `ErrBurstExceeded` | `AllowN` or `WaitN` asked for more tokens than `Burst`. |
| `ErrStore` | The store failed. Unwrap for the underlying error. |
| `ErrClosed` | The gate or store was used after `Close`. |

Match with `errors.Is`. A denied request is not an error: `Allow` returns `(false, nil)`.

## Testing

Inject a `Clock` to advance time without sleeping:

```go
clk := gatekeep.NewFakeClock(time.Unix(0, 0))
gate, _ := gatekeep.New(gatekeep.Limiter{
	Rate:  gatekeep.PerSecond(1),
	Burst: 1,
	Clock: clk,
})

ok, _ := gate.Allow("k") // true, bucket now empty
ok, _ = gate.Allow("k")  // false

clk.Advance(time.Second)
ok, _ = gate.Allow("k") // true
```

`FakeClock` also releases `Wait` sleepers when time advances, so `Wait` is testable without real delays. The Redis store reads its clock from the server and ignores the injected one; test it against a real Redis instance.

## Limits of the design

- Token bucket allows short bursts by design. If a downstream system cannot absorb `Burst` requests at once, lower `Burst`.
- The in-memory store enforces per process, not per cluster.
- With the Redis store, every decision costs one round trip. Budget for that latency on the request path, and set a context deadline.
- `Wait` is not fair between goroutines.
- Denied requests still cost a store call. Rate limiting protects your handlers, not your front door; pair it with connection limits for that.

## License

MIT. See [LICENSE](LICENSE).
