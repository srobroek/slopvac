# gatekeep

`gatekeep` provides token-bucket rate limiting for Go applications. It supports independent buckets per key, Redis and in-memory storage, and middleware for `net/http`.

## Install

Add `gatekeep` to your Go module:

```bash
go get <module-path>/gatekeep
```

Replace `<module-path>` with the module path declared by the `gatekeep` repository.

## Usage

Create a limiter with a rate, burst capacity, and bucket TTL:

```go
limiter := gatekeep.Limiter{
	Rate:  10,
	Burst: 20,
	TTL:   time.Minute,
}
```

Call `Allow` with a key to check whether the request can consume one token:

```go
if !limiter.Allow("user:42") {
	http.Error(w, "rate limit exceeded", http.StatusTooManyRequests)
	return
}

next.ServeHTTP(w, r)
```

Each key uses an independent token bucket. For example, `user:42` and `user:43` do not consume tokens from the same bucket.

## Wait for capacity

Call `Wait` when the handler should block until a token becomes available or the context ends:

```go
if err := limiter.Wait(ctx, "user:42"); err != nil {
	http.Error(w, err.Error(), http.StatusTooManyRequests)
	return
}

next.ServeHTTP(w, r)
```

`Wait` returns the context error when `ctx` is canceled or reaches its deadline.

## Configuration

| Field | Type | Default | Effect |
| --- | --- | --- | --- |
| `Rate` | `float64` | `0` | Controls the token refill rate. |
| `Burst` | `int` | `0` | Sets the maximum number of tokens a bucket can hold. |
| `TTL` | `time.Duration` | `0` | Sets how long an inactive key remains in the store. |

Set `Burst` to the maximum number of requests that a key can make before it must wait for refills.

Set `Rate` to the number of tokens the limiter replenishes over the configured rate interval.

Set `TTL` to remove inactive per-key buckets from the selected store.

## Storage

`gatekeep` supports two storage backends.

### In-memory storage

Use the in-memory store for a single process. Each process maintains its own buckets.

This backend does not share rate-limit state between application instances.

### Redis storage

Use the Redis store when multiple application instances must share bucket state.

Configure all instances to use the same Redis deployment and compatible limiter settings.

Redis availability affects requests that require a bucket operation. Configure Redis connection behavior in the Redis store according to your application’s failure policy.

## HTTP middleware

Use the `net/http` middleware to apply one limiter to incoming requests.

Configure the middleware to derive a key from each request. Common keys include a user identifier, API key, or client address.

The middleware checks the key before it invokes the wrapped handler. Requests without an available token receive a rate-limit response and do not reach the wrapped handler.

## Choosing a key

Choose a key that matches the resource you want to protect:

```text
user:<user-id>       Limits each authenticated user.
api-key:<key-id>     Limits each API consumer.
ip:<client-address>  Limits each client address.
route:<route-name>   Limits all clients sharing one route.
```

Do not use one constant key when you need independent limits for multiple clients.

## License

See the repository license file.
