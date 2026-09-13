# gatekeep

`gatekeep` provides per-key token-bucket rate limiting with in-memory storage, Redis storage, and `net/http` middleware.

## Install

Replace `MODULE_PATH` with the module path from the repository’s `go.mod` file.

```sh
go get MODULE_PATH
```

## Usage

Create a limiter configuration with a refill rate, burst capacity, and bucket expiration period.

```go
config := gatekeep.Limiter{
	Rate:  10,
	Burst: 20,
	TTL:   5 * time.Minute,
}
```

Select the in-memory store for one Go process.

```go
store := gatekeep.NewMemoryStore()
limiter := gatekeep.New(config, store)
```

`Allow` consumes one token for the supplied key.

```go
if !limiter.Allow("account:42") {
	return errors.New("rate limit exceeded")
}
```

Each distinct key uses a separate token bucket. Use stable keys such as account IDs, API keys, or tenant IDs.

### Wait for a token

`Wait` blocks until the key receives a token or the context ends.

```go
ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
defer cancel()

if err := limiter.Wait(ctx, "account:42"); err != nil {
	return err
}
```

Use a context deadline to limit how long a request can wait.

## Stores

### In-memory store

The in-memory store keeps bucket state inside one Go process. Restarting the process removes its bucket state.

```go
store := gatekeep.NewMemoryStore()
limiter := gatekeep.New(config, store)
```

Use this store when one process owns all requests for each key.

### Redis store

The Redis store shares bucket state across processes that use the same Redis deployment.

```go
store := gatekeep.NewRedisStore(redisClient)
limiter := gatekeep.New(config, store)
```

Configure every process with the same rate, burst, TTL, and key format.

## `net/http` middleware

Wrap an `http.Handler` and return one stable key for each request.

```go
keyFunc := func(r *http.Request) string {
	return r.Header.Get("X-API-Key")
}

handler := gatekeep.Middleware(limiter, keyFunc)(applicationHandler)

server := &http.Server{
	Addr:    ":8080",
	Handler: handler,
}
```

The middleware applies the selected key’s bucket before calling `applicationHandler`.

## Configuration

| Name | Type | Default | Effect |
| --- | --- | --- | --- |
| `Rate` | Numeric rate | Required | Sets the number of tokens added per second. |
| `Burst` | `int` | Required | Sets the maximum number of tokens that one bucket can hold. |
| `TTL` | `time.Duration` | Required | Sets how long the store retains inactive bucket state. |

A burst value of `20` permits up to 20 immediate requests when the bucket contains 20 tokens. A rate of `10` then adds 10 tokens per second.
